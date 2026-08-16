import uuid
import re
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

from app.models.dataset import ProcessingStateEnum
from app.models.quality import (
    QualityReport, QualityScore, QualityIssue, QualityDimensionEnum, SeverityEnum, DimensionBreakdown
)
from app.models.profiling import ColumnTypeEnum, SemanticHintEnum
from app.core.number_parsing import to_numeric_series
from app.services.dataset_service import DatasetService
from app.services.profiler_service import ProfilerService

QUALITY_CACHE: Dict[str, QualityReport] = {}

def _safe_evidence_sample(sample_list: Any) -> List[Any]:
    if hasattr(sample_list, "tolist"):
        sample_list = sample_list.tolist()
    elif not isinstance(sample_list, list):
        sample_list = [sample_list]

    cleaned = []
    for item in sample_list:
        if isinstance(item, (list, tuple, np.ndarray)):
            cleaned.append(str(item))
        else:
            try:
                if pd.isna(item):
                    cleaned.append("[VALOR VACÍO]")
                elif isinstance(item, (bool, np.bool_)):
                    cleaned.append(bool(item))
                elif isinstance(item, (int, np.integer)):
                    cleaned.append(int(item))
                elif isinstance(item, (float, np.floating)):
                    f = float(item)
                    cleaned.append(None if np.isnan(f) or np.isinf(f) else f)
                else:
                    cleaned.append(str(item))
            except Exception:
                cleaned.append(str(item))
    return cleaned

class QualityService:
    @staticmethod
    def analyze_quality(dataset_id: str) -> QualityReport:
        profiling = ProfilerService.get_profiling_report(dataset_id)
        df = DatasetService.load_dataframe(dataset_id)
        metadata = DatasetService.get_dataset_metadata(dataset_id)

        row_count, col_count = df.shape
        total_cells = row_count * col_count if row_count * col_count > 0 else 1

        issues: List[QualityIssue] = []

        # ==========================================
        # 1. DATOS COMPLETOS (Completeness)
        # ==========================================
        total_null_cells = 0
        for col_prof in profiling.columns:
            total_null_cells += col_prof.null_count
            if col_prof.null_count > 0:
                null_pct = col_prof.null_percentage
                severity = SeverityEnum.CRITICAL if null_pct > 50 else (SeverityEnum.HIGH if null_pct > 20 else SeverityEnum.MEDIUM)
                issues.append(QualityIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    dimension=QualityDimensionEnum.COMPLETENESS,
                    severity=severity,
                    column=col_prof.column_name,
                    description=f"La columna '{col_prof.column_name}' presenta {col_prof.null_count} valores nulos ({null_pct}%).",
                    affected_rows=col_prof.null_count,
                    affected_percentage=null_pct,
                    evidence_sample=["[VALOR VACÍO]"],
                    suggested_action=f"Imputar nulos en '{col_prof.column_name}' mediante mediana o constante ('fill_missing')."
                ))

        completeness_score = round(max(0.0, 100.0 * (1.0 - (total_null_cells / total_cells))), 2)

        # ==========================================
        # 2. REGISTROS ÚNICOS (Uniqueness)
        # ==========================================
        duplicates_count = profiling.duplicates_count
        duplicates_pct = profiling.duplicates_percentage
        if duplicates_count > 0:
            issues.append(QualityIssue(
                issue_id=str(uuid.uuid4())[:8],
                dimension=QualityDimensionEnum.UNIQUENESS,
                severity=SeverityEnum.HIGH if duplicates_pct > 5 else SeverityEnum.MEDIUM,
                column=None,
                description=f"Se han encontrado {duplicates_count} filas exactas duplicadas ({duplicates_pct}%).",
                affected_rows=duplicates_count,
                affected_percentage=duplicates_pct,
                evidence_sample=[f"{duplicates_count} registros idénticos"],
                suggested_action="Eliminar filas duplicadas ('remove_duplicates')."
            ))

        uniqueness_score = round(max(0.0, 100.0 * (1.0 - (duplicates_count / row_count))), 2) if row_count > 0 else 100.0

        # ==========================================
        # 3. FORMATO HOMOGÉNEO (Consistency)
        # ==========================================
        inconsistent_cells = 0
        for col_prof in profiling.columns:
            series = df[col_prof.column_name].dropna().astype(str)
            if not len(series):
                continue

            has_whitespace = series.apply(lambda x: x != x.strip() or "  " in x)
            whitespace_count = int(has_whitespace.sum())

            if whitespace_count > 0:
                inconsistent_cells += whitespace_count
                pct = round((whitespace_count / row_count) * 100, 2)
                issues.append(QualityIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    dimension=QualityDimensionEnum.CONSISTENCY,
                    severity=SeverityEnum.LOW,
                    column=col_prof.column_name,
                    description=f"La columna '{col_prof.column_name}' contiene {whitespace_count} valores con espacios sobrantes o dobles.",
                    affected_rows=whitespace_count,
                    affected_percentage=pct,
                    evidence_sample=_safe_evidence_sample(series[has_whitespace].head(3)),
                    suggested_action=f"Limpiar espacios en blanco en '{col_prof.column_name}' ('trim_text')."
                ))

            if col_prof.inferred_type in [ColumnTypeEnum.TEXT, ColumnTypeEnum.CATEGORICAL] or col_prof.semantic_hint == SemanticHintEnum.NAME:
                cleaned_str = series.str.strip().str.lower()
                unique_original = series.str.strip().nunique()
                unique_lower = cleaned_str.nunique()

                # Detectar mayúsculas completas en cadenas largas (>2 caracteres)
                has_all_caps = series.apply(lambda x: len(x.strip()) > 2 and x.strip().isupper())
                all_caps_count = int(has_all_caps.sum())

                if unique_original > unique_lower or all_caps_count > 0:
                    diff_count = max(unique_original - unique_lower, all_caps_count)
                    inconsistent_cells += diff_count
                    issues.append(QualityIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        dimension=QualityDimensionEnum.CONSISTENCY,
                        severity=SeverityEnum.MEDIUM,
                        column=col_prof.column_name,
                        description=f"Inconsistencia de formato (mayúsculas/minúsculas) en '{col_prof.column_name}' ({diff_count} valores detectados).",
                        affected_rows=diff_count,
                        affected_percentage=round((diff_count / row_count) * 100, 2),
                        evidence_sample=_safe_evidence_sample(series[has_all_caps].head(3) if all_caps_count > 0 else series.unique()[:3]),
                        suggested_action=f"Normalizar formato de texto en '{col_prof.column_name}' a Title Case ('normalize_case')."
                    ))

        consistency_score = round(max(0.0, 100.0 * (1.0 - (inconsistent_cells / total_cells))), 2)

        # ==========================================
        # 4. FORMATOS VÁLIDOS (Validity)
        # ==========================================
        invalid_cells = 0
        for col_prof in profiling.columns:
            series = df[col_prof.column_name].dropna().astype(str).str.strip()
            if not len(series):
                continue

            # Fechas
            if col_prof.semantic_hint == SemanticHintEnum.DATE or col_prof.inferred_type == ColumnTypeEnum.DATETIME:
                parsed_dates = pd.to_datetime(series, errors="coerce")
                invalid_dates_count = int(parsed_dates.isna().sum())

                if invalid_dates_count > 0:
                    invalid_cells += invalid_dates_count
                    pct = round((invalid_dates_count / row_count) * 100, 2)
                    issues.append(QualityIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        dimension=QualityDimensionEnum.VALIDITY,
                        severity=SeverityEnum.HIGH,
                        column=col_prof.column_name,
                        description=f"La columna de fecha '{col_prof.column_name}' contiene {invalid_dates_count} valores con formato no estándar o inválido.",
                        affected_rows=invalid_dates_count,
                        affected_percentage=pct,
                        evidence_sample=_safe_evidence_sample(series[parsed_dates.isna()].head(3)),
                        suggested_action=f"Convertir columna a formato fecha estándar ISO 8601 ('convert_datetime')."
                    ))

            # Símbolos o marcadores en columnas cuantitativas
            is_quant_column = (
                col_prof.inferred_type == ColumnTypeEnum.NUMERIC or
                col_prof.semantic_hint in [SemanticHintEnum.CURRENCY, SemanticHintEnum.PERCENTAGE] or
                any(k in col_prof.column_name.lower() for k in ["precio", "salario", "sueldo", "horas", "dias", "cantidad", "unidades", "llamadas", "aht", "segundos", "minutos", "importe", "monto"])
            )

            if is_quant_column:
                # Detectar símbolos monetarios/porcentuales o marcadores de texto N/D, N/A, -
                placeholders = ["n/d", "n/a", "nd", "na", "-", "null", "none", "nan"]
                has_placeholders = series.apply(lambda x: x.lower().strip() in placeholders)
                has_symbols = series.apply(lambda x: any(sym in x for sym in ["€", "$", "%", "USD", "EUR"]))
                dirty_mask = has_placeholders | has_symbols
                dirty_count = int(dirty_mask.sum())

                if dirty_count > 0:
                    invalid_cells += dirty_count
                    issues.append(QualityIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        dimension=QualityDimensionEnum.VALIDITY,
                        severity=SeverityEnum.MEDIUM,
                        column=col_prof.column_name,
                        description=f"La columna cuantitativa '{col_prof.column_name}' contiene {dirty_count} celdas con símbolos o marcadores de texto (N/D, N/A, €/$).",
                        affected_rows=dirty_count,
                        affected_percentage=round((dirty_count / row_count) * 100, 2),
                        evidence_sample=_safe_evidence_sample(series[dirty_mask].head(3)),
                        suggested_action=f"Limpiar símbolos y convertir '{col_prof.column_name}' a número puro float64 ('convert_numeric')."
                    ))

        validity_score = round(max(0.0, 100.0 * (1.0 - (invalid_cells / total_cells))), 2)

        # ==========================================
        # 5. REGLAS DE NEGOCIO (Integrity)
        # ==========================================
        integrity_violations = 0
        for col_prof in profiling.columns:
            col_name = col_prof.column_name
            col_lower = col_name.lower()

            # Parseo centralizado: soporta símbolos y separadores europeos/americanos
            series_num = to_numeric_series(df[col_name]).dropna()

            if not len(series_num):
                continue

            # A. Regla Porcentual: [0.0, 100.0]
            is_percentage = (
                col_prof.semantic_hint == SemanticHintEnum.PERCENTAGE or
                any(k in col_lower for k in ["_pct", "pct", "porcentaje", "productividad", "conversion", "score", "calidad", "tasa", "ratio", "rate"])
            )
            if is_percentage:
                out_of_bounds = series_num[(series_num > 100.0) | (series_num < 0.0)]
                if len(out_of_bounds) > 0:
                    count = len(out_of_bounds)
                    integrity_violations += count
                    issues.append(QualityIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        dimension=QualityDimensionEnum.INTEGRITY,
                        severity=SeverityEnum.HIGH,
                        column=col_name,
                        description=f"Violación de rango porcentual: Se detectaron {count} valor(es) fuera del intervalo de negocio [0 - 100%] en '{col_name}'.",
                        affected_rows=count,
                        affected_percentage=round((count / row_count) * 100, 2),
                        evidence_sample=_safe_evidence_sample(out_of_bounds.head(3)),
                        suggested_action=f"Acotar valores al rango [0.0, 100.0] en '{col_name}' ('clamp_range')."
                    ))

            # B. Regla Conteo / Magnitud Positiva: [0.0, inf]
            is_positive_count_or_time = (
                col_prof.semantic_hint == SemanticHintEnum.CURRENCY or
                any(k in col_lower for k in ["cantidad", "unidades", "llamadas", "hours", "horas", "dias", "absentismo", "aht", "segundos", "minutos", "precio", "salario", "sueldo", "monto", "importe"])
            )
            if is_positive_count_or_time and not is_percentage:
                negatives = series_num[series_num < 0.0]
                if len(negatives) > 0:
                    count = len(negatives)
                    integrity_violations += count
                    issues.append(QualityIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        dimension=QualityDimensionEnum.INTEGRITY,
                        severity=SeverityEnum.HIGH,
                        column=col_name,
                        description=f"Violación de regla de negocio: Se detectaron {count} valor(es) negativos imposibles en '{col_name}'.",
                        affected_rows=count,
                        affected_percentage=round((count / row_count) * 100, 2),
                        evidence_sample=_safe_evidence_sample(negatives.head(3)),
                        suggested_action=f"Acotar valores negativos al piso mínimo 0 en '{col_name}' ('clamp_range')."
                    ))

        integrity_score = round(max(0.0, 100.0 * (1.0 - (integrity_violations / row_count))), 2) if row_count > 0 else 100.0

        # ==========================================
        # FÓRMULA DE OVERALL SCORE
        # ==========================================
        overall = (
            (0.30 * completeness_score) +
            (0.25 * validity_score) +
            (0.20 * consistency_score) +
            (0.15 * uniqueness_score) +
            (0.10 * integrity_score)
        )
        overall_score = round(max(0.0, min(100.0, overall)), 1)

        completeness_issues = len([i for i in issues if i.dimension == QualityDimensionEnum.COMPLETENESS])
        validity_issues = len([i for i in issues if i.dimension == QualityDimensionEnum.VALIDITY])
        consistency_issues = len([i for i in issues if i.dimension == QualityDimensionEnum.CONSISTENCY])
        uniqueness_issues = len([i for i in issues if i.dimension == QualityDimensionEnum.UNIQUENESS])
        integrity_issues = len([i for i in issues if i.dimension == QualityDimensionEnum.INTEGRITY])

        score_obj = QualityScore(
            overall_score=overall_score,
            completeness=DimensionBreakdown(
                score=completeness_score, weight=0.30, issues_count=completeness_issues,
                summary=f"Datos completos al {completeness_score}% ({total_null_cells} celdas vacías)."
            ),
            validity=DimensionBreakdown(
                score=validity_score, weight=0.25, issues_count=validity_issues,
                summary=f"Formatos válidos al {validity_score}% ({invalid_cells} celdas con tipo/fecha incorrecta)."
            ),
            consistency=DimensionBreakdown(
                score=consistency_score, weight=0.20, issues_count=consistency_issues,
                summary=f"Formato homogéneo al {consistency_score}% ({inconsistent_cells} desvíos de formato/espacios)."
            ),
            uniqueness=DimensionBreakdown(
                score=uniqueness_score, weight=0.15, issues_count=uniqueness_issues,
                summary=f"Registros únicos al {uniqueness_score}% ({duplicates_count} filas duplicadas)."
            ),
            integrity=DimensionBreakdown(
                score=integrity_score, weight=0.10, issues_count=integrity_issues,
                summary=f"Reglas de negocio al {integrity_score}% ({integrity_violations} desvíos de coherencia)."
            ),
            explanation=(
                f"El dataset obtiene un Data Quality Score de {overall_score}/100. "
                f"Se han identificado {len(issues)} problemas accionables. "
                f"Principales áreas de mejora: Datos Completos ({completeness_score}%) y Formatos Válidos ({validity_score}%)."
            )
        )

        report = QualityReport(
            dataset_id=dataset_id,
            quality_score=score_obj,
            issues=issues,
            issues_count=len(issues),
            generated_at=datetime.now(timezone.utc)
        )

        metadata.status = ProcessingStateEnum.QUALITY_ANALYZED
        QUALITY_CACHE[dataset_id] = report
        return report

    @staticmethod
    def get_quality_report(dataset_id: str) -> QualityReport:
        if dataset_id in QUALITY_CACHE:
            return QUALITY_CACHE[dataset_id]
        return QualityService.analyze_quality(dataset_id)
