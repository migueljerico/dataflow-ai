import re
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

from app.models.dataset import ProcessingStateEnum
from app.models.profiling import (
    ProfilingReport, ColumnProfile, ColumnTypeEnum, SemanticHintEnum
)
from app.core.number_parsing import to_numeric_series, MISSING_MARKERS
from app.services.dataset_service import DatasetService

PROFILING_CACHE: Dict[str, ProfilingReport] = {}

def _safe_float(val: Any) -> Any:
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        return None if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return None

def _safe_sample_values(sample_vals: List[Any]) -> List[Any]:
    cleaned = []
    for v in sample_vals:
        if pd.isna(v) or v is None:
            cleaned.append(None)
        elif isinstance(v, (bool, np.bool_)):
            cleaned.append(bool(v))
        elif isinstance(v, (int, np.integer)):
            cleaned.append(int(v))
        elif isinstance(v, (float, np.floating)):
            f = float(v)
            cleaned.append(None if np.isnan(f) or np.isinf(f) else f)
        else:
            cleaned.append(str(v))
    return cleaned

class ProfilerService:
    @staticmethod
    def _detect_semantic_hint(col_name: str, series: pd.Series, inferred_type: ColumnTypeEnum) -> SemanticHintEnum:
        col_lower = col_name.lower().strip()
        non_null_str = series.dropna().astype(str)

        if not len(non_null_str):
            return SemanticHintEnum.UNKNOWN

        # 1. Email
        if "email" in col_lower or any("@" in val for val in non_null_str.head(20)):
            return SemanticHintEnum.EMAIL

        # 2. Percentage / Ratios (Exige evidencia de % en datos o sufijos explícitos validados contra la distribución)
        has_percent_symbol = any("%" in val for val in non_null_str.head(50))
        if has_percent_symbol:
            return SemanticHintEnum.PERCENTAGE

        has_explicit_pct_name = (
            col_lower.endswith(("_pct", "_percentage", "_porcentaje", "_rate", "_ratio", "_tasa", "_score")) or
            col_lower.startswith(("pct_", "porcentaje_", "tasa_", "ratio_", "score_")) or
            col_lower in ["%", "pct", "porcentaje", "ctr", "cvr", "roi", "score", "score_calidad", "tasa_conversion", "conversion_rate", "churn_rate", "descuento_pct", "incidencias_pct"]
        )
        if has_explicit_pct_name:
            return SemanticHintEnum.PERCENTAGE

        # 3. Currency / Dinero
        if any(keyword in col_lower for keyword in ["precio", "importe", "coste", "salario", "sueldo", "monto", "price", "amount", "revenue"]):
            return SemanticHintEnum.CURRENCY
        if any(symbol in val for val in non_null_str.head(20) for symbol in ["€", "$", "USD", "EUR"]):
            return SemanticHintEnum.CURRENCY

        # 4. Dates
        if any(keyword in col_lower for keyword in ["fecha", "date", "created", "updated", "ingreso", "alta", "baja"]):
            return SemanticHintEnum.DATE
        if inferred_type == ColumnTypeEnum.DATETIME:
            return SemanticHintEnum.DATE

        # 5. ID / Code
        if (
            col_lower.startswith("id") or
            col_lower.endswith("_id") or
            col_lower.startswith("cod") or
            col_lower.endswith("_cod") or
            "codigo" in col_lower or
            "code" in col_lower or
            "cif" in col_lower or
            "dni" in col_lower or
            "nif" in col_lower or
            "sku" in col_lower or
            "ref" in col_lower or
            "referencia" in col_lower or
            "pedido" in col_lower or
            "factura" in col_lower or
            "ticket" in col_lower or
            "albaran" in col_lower
        ):
            return SemanticHintEnum.ID
        if any(re.match(r"^[A-Za-z0-9]{2,6}[-_][A-Za-z0-9]{1,}$", val.strip()) for val in non_null_str.head(20)):
            return SemanticHintEnum.ID

        # 6. Phone
        if "telefono" in col_lower or "phone" in col_lower or "movil" in col_lower:
            return SemanticHintEnum.PHONE

        # 7. Name / Entity
        if any(k in col_lower for k in ["nombre", "name", "cliente", "empleado", "agente", "comercial", "contacto", "persona", "usuario"]):
            return SemanticHintEnum.NAME

        # 8. Location
        if any(k in col_lower for k in ["pais", "ciudad", "provincia", "region", "location", "country", "city"]):
            return SemanticHintEnum.LOCATION

        return SemanticHintEnum.UNKNOWN

    @staticmethod
    def _infer_column_type(series: pd.Series) -> ColumnTypeEnum:
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return ColumnTypeEnum.TEXT

        # 1. Numeric
        if pd.api.types.is_numeric_dtype(series):
            return ColumnTypeEnum.NUMERIC

        # Check if text contains convertible numeric values or symbols
        try:
            # Parseo centralizado con soporte de separadores europeos/americanos y marcadores ampliados
            as_str = non_null_series.astype(str).str.strip()
            is_marker = as_str.str.lower().isin(MISSING_MARKERS) | as_str.str.match(r"^[-_—–\s]+$")
            converted = to_numeric_series(non_null_series)
            valid_numeric_count = int(converted.notna().sum())
            total_non_null = len(non_null_series)

            if total_non_null > 0:
                non_marker_count = int((~is_marker).sum())
                # Si todos los elementos que no son marcadores se convierten a número
                if non_marker_count > 0 and converted[~is_marker].notna().all():
                    return ColumnTypeEnum.NUMERIC
                # Si al menos un 50% de los valores se parsean exitosamente a número
                if valid_numeric_count > 0 and (valid_numeric_count / total_non_null) >= 0.5:
                    return ColumnTypeEnum.NUMERIC
        except (ValueError, TypeError):
            pass

        # 2. Datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return ColumnTypeEnum.DATETIME
        try:
            sample = non_null_series.astype(str).head(20)
            sample_filtered = sample[~sample.str.lower().isin(["invalid_date", "error", "n/d", "n/a", "--", "-"])]
            if len(sample_filtered) > 0:
                parsed = pd.to_datetime(sample_filtered, errors="coerce")
                if parsed.notna().sum() / len(sample_filtered) > 0.6:
                    return ColumnTypeEnum.DATETIME
        except Exception:
            pass

        # 3. Boolean
        unique_vals = set(non_null_series.astype(str).str.lower().unique())
        if unique_vals.issubset({"true", "false", "si", "no", "s", "n", "1", "0", "yes", "y"}):
            return ColumnTypeEnum.BOOLEAN

        # 4. Categorical vs Text
        unique_ratio = len(series.unique()) / len(series)
        if unique_ratio < 0.25 and len(series.unique()) <= 30:
            return ColumnTypeEnum.CATEGORICAL

        return ColumnTypeEnum.TEXT

    @staticmethod
    def profile_dataset(dataset_id: str) -> ProfilingReport:
        metadata = DatasetService.get_dataset_metadata(dataset_id)
        df = DatasetService.load_dataframe(dataset_id)

        row_count, col_count = df.shape
        duplicates_count = int(df.duplicated().sum())
        duplicates_pct = round((duplicates_count / row_count) * 100, 2) if row_count > 0 else 0.0
        memory_bytes = int(df.memory_usage(deep=True).sum())

        column_profiles: List[ColumnProfile] = []
        global_warnings: List[str] = []

        if duplicates_count > 0:
            global_warnings.append(f"Se detectaron {duplicates_count} filas exactas duplicadas ({duplicates_pct}% del dataset).")

        for col_name in df.columns:
            series = df[col_name]
            clean_series = series.replace(r'^\s*$', np.nan, regex=True)
            null_count = int(clean_series.isna().sum())
            null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0.0
            unique_count = int(clean_series.nunique())

            sample_vals = clean_series.dropna().unique()[:5].tolist()
            sample_vals_clean = _safe_sample_values(sample_vals)

            inferred_type = ProfilerService._infer_column_type(clean_series)
            semantic_hint = ProfilerService._detect_semantic_hint(col_name, clean_series, inferred_type)

            col_warnings: List[str] = []
            if null_pct > 20.0:
                col_warnings.append(f"Alto nivel de nulos: {null_pct}% de valores faltantes.")
            if unique_count == 1 and row_count > 1:
                col_warnings.append("Columna de valor constante (todos los registros tienen el mismo valor).")
            if inferred_type == ColumnTypeEnum.TEXT and unique_count == row_count and row_count > 1:
                col_warnings.append("Alta cardinalidad: todos los valores de texto son únicos.")

            min_val, max_val, mean_val, median_val, std_val = None, None, None, None, None
            if inferred_type == ColumnTypeEnum.NUMERIC:
                num_series = to_numeric_series(clean_series).dropna()

                if len(num_series) > 0:
                    min_val = _safe_float(num_series.min())
                    max_val = _safe_float(num_series.max())
                    mean_val = _safe_float(round(num_series.mean(), 2))
                    median_val = _safe_float(round(num_series.median(), 2))
                    std_val = _safe_float(round(num_series.std(), 2)) if len(num_series) > 1 else 0.0

            profile = ColumnProfile(
                column_name=str(col_name),
                inferred_type=inferred_type,
                semantic_hint=semantic_hint,
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                sample_values=sample_vals_clean,
                min_value=min_val,
                max_value=max_val,
                mean=mean_val,
                median=median_val,
                std=std_val,
                warnings=col_warnings
            )
            column_profiles.append(profile)

        report = ProfilingReport(
            dataset_id=dataset_id,
            row_count=row_count,
            column_count=col_count,
            duplicates_count=duplicates_count,
            duplicates_percentage=duplicates_pct,
            memory_estimate_bytes=memory_bytes,
            columns=column_profiles,
            global_warnings=global_warnings,
            generated_at=datetime.now(timezone.utc)
        )

        metadata.status = ProcessingStateEnum.PROFILED
        PROFILING_CACHE[dataset_id] = report
        return report

    @staticmethod
    def get_profiling_report(dataset_id: str) -> ProfilingReport:
        if dataset_id in PROFILING_CACHE:
            return PROFILING_CACHE[dataset_id]
        return ProfilerService.profile_dataset(dataset_id)
