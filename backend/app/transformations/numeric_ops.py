import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from app.transformations.base import BaseTransformation
from app.core.exceptions import FunctionalException

class ConvertNumericTransformation(BaseTransformation):
    operation_name = "convert_numeric"
    description = "Limpia símbolos de moneda/porcentaje y texto N/D o N/A, convirtiendo la columna a número float/int."
    risk = "medium"

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        df_copy = df.copy()

        original_series = df_copy[col].astype(str)
        cleaned = (
            original_series
            .str.replace("€", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("USD", "", regex=False)
            .str.replace("EUR", "", regex=False)
            .str.strip()
        )
        
        # Reemplazar marcadores de texto N/D, N/A, -, null por NaN explícito
        placeholders = ["n/d", "n/a", "nd", "na", "-", "null", "none", "nan", "undefined", ""]
        cleaned = cleaned.apply(lambda x: np.nan if str(x).lower().strip() in placeholders else x)

        converted = pd.to_numeric(cleaned, errors="coerce")
        
        # Conteo preciso evitando el falso positivo de NaN != NaN
        changed = (original_series != converted.astype(str)) & ~(original_series.isin(["nan", "None", ""]) & converted.isna())
        affected = int(changed.sum())
        df_copy[col] = converted
        return df_copy, affected


class RoundNumericTransformation(BaseTransformation):
    operation_name = "round_numeric"
    description = "Redondea una columna numérica a N decimales."
    risk = "low"

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        decimals = parameters.get("decimals", 2)
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if not isinstance(decimals, int) or decimals < 0:
            raise FunctionalException(message="El parámetro 'decimals' debe ser un número entero >= 0.", code="INVALID_PARAMETER")

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

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

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
