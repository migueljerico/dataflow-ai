from typing import Any, Dict, Tuple

import pandas as pd
from app.core.exceptions import FunctionalException
from app.core.number_parsing import is_missing_series, to_numeric_series
from app.transformations.base import BaseTransformation


class ConvertNumericTransformation(BaseTransformation):
    operation_name = "convert_numeric"
    description = "Limpia símbolos de moneda/porcentaje y texto N/D o N/A, convirtiendo la columna a número float/int."
    risk = "medium"
    reversible = False
    allowed_parameters = ["column"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna numérica a convertir"}
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        df_copy = df.copy()

        # Cinturón de seguridad contra pérdida de datos:
        # Si más del 50% de las celdas con contenido real (excluyendo marcadores de ausencia)
        # terminan en NaN tras la conversión, abortar la operación con FunctionalException.
        missing_mask = is_missing_series(df_copy[col])
        real_content = df_copy[col][~missing_mask]
        total_real = len(real_content)
        if total_real > 0:
            parsed_real = to_numeric_series(real_content)
            lost_count = int(parsed_real.isna().sum())
            loss_ratio = lost_count / total_real
            if loss_ratio > 0.5:
                sample_lost = str(real_content[parsed_real.isna()].iloc[0]) if lost_count > 0 else ""
                loss_pct = round(loss_ratio * 100, 1)
                raise FunctionalException(
                    message=(
                        f"Conversión a numérico abortada en '{col}': el {loss_pct}% de las celdas con datos reales "
                        f"({lost_count}/{total_real}) no son numéricas y se perderían como NaN (ej. '{sample_lost[:50]}')."
                    ),
                    code="CONVERT_NUMERIC_DATA_LOSS",
                    details={
                        "column": col,
                        "lost_count": lost_count,
                        "total_real": total_real,
                        "loss_ratio": loss_ratio,
                    },
                )

        original_series = df_copy[col].astype(str)
        converted = to_numeric_series(original_series)

        # Conteo preciso evitando el falso positivo de NaN != NaN.
        # En pandas >= 3 astype(str) conserva los NaN como missing values.
        orig_missing = original_series.isna() | original_series.isin(["nan", "None", ""])
        changed = (original_series != converted.astype(str)) & ~(orig_missing & converted.isna())
        affected = int(changed.sum())
        df_copy[col] = converted
        return df_copy, affected


class RoundNumericTransformation(BaseTransformation):
    operation_name = "round_numeric"
    description = "Redondea una columna numérica a N decimales."
    risk = "low"
    reversible = True
    allowed_parameters = ["column", "decimals"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna a redondear"},
        "decimals": {"type": "integer", "required": False, "default": 2, "description": "Número de decimales (>=0)"},
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        decimals = parameters.get("decimals", 2)
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if not isinstance(decimals, int) or decimals < 0:
            raise FunctionalException(
                message="El parámetro 'decimals' debe ser un número entero >= 0.", code="INVALID_PARAMETER"
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        decimals = parameters.get("decimals", 2)
        df_copy = df.copy()

        original_series = pd.to_numeric(df_copy[col], errors="coerce")
        rounded = original_series.round(decimals)

        changed = (original_series != rounded) & ~(original_series.isna() & rounded.isna())
        affected = int(changed.sum())
        df_copy[col] = rounded
        return df_copy, affected


class ClampRangeTransformation(BaseTransformation):
    operation_name = "clamp_range"
    description = "Corrige y limita valores numéricos fuera de rango de negocio (e.g. valores negativos a 0 o scores > 100 a 100)."
    risk = "medium"
    reversible = False
    allowed_parameters = ["column", "min_value", "max_value"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna a acotar"},
        "min_value": {"type": "number", "required": False, "description": "Límite inferior opcional"},
        "max_value": {"type": "number", "required": False, "description": "Límite superior opcional"},
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        min_val = parameters.get("min_value")
        max_val = parameters.get("max_value")
        if min_val is not None and not isinstance(min_val, (int, float)):
            raise FunctionalException(message="El parámetro 'min_value' debe ser numérico.", code="INVALID_PARAMETER")
        if max_val is not None and not isinstance(max_val, (int, float)):
            raise FunctionalException(message="El parámetro 'max_value' debe ser numérico.", code="INVALID_PARAMETER")
        if min_val is not None and max_val is not None and min_val > max_val:
            raise FunctionalException(
                message="'min_value' no puede ser mayor que 'max_value'.", code="INVALID_PARAMETER"
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        min_val = parameters.get("min_value")
        max_val = parameters.get("max_value")
        df_copy = df.copy()

        num_series = pd.to_numeric(df_copy[col], errors="coerce")
        original_series = num_series.copy()

        if min_val is not None:
            num_series = num_series.apply(lambda x: min_val if pd.notna(x) and x < min_val else x)
        if max_val is not None:
            num_series = num_series.apply(lambda x: max_val if pd.notna(x) and x > max_val else x)

        # Corrección del bug IEEE 754: NaN != NaN siempre es True. Excluir NaNs del conteo de modificados
        changed = (original_series != num_series) & ~(original_series.isna() & num_series.isna())
        affected = int(changed.sum())
        df_copy[col] = num_series
        return df_copy, affected
