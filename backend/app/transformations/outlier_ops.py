from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation


class DetectOutliersIQRTransformation(BaseTransformation):
    operation_name = "detect_outliers_iqr"
    description = (
        "Detecta y gestiona valores atípicos mediante el Rango Intercuartílico (IQR), "
        "con soporte para acotar (cap), anular (nullify), eliminar filas (drop) o marcar (flag)."
    )
    risk = "medium"
    reversible = False
    allowed_parameters = ["column", "multiplier", "action", "lower_quantile", "upper_quantile"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Columna numérica a analizar"},
        "multiplier": {
            "type": "number",
            "required": False,
            "default": 1.5,
            "description": "Multiplicador del IQR (ej. 1.5 para outliers estándar, 3.0 para extremos)",
        },
        "action": {
            "type": "string",
            "required": False,
            "default": "cap",
            "enum": ["cap", "nullify", "drop", "flag"],
            "description": "Acción sobre los outliers: 'cap' (acotar límites), 'nullify' (hacer NaN), 'drop' (eliminar filas), 'flag' (crear columna booleana)",
        },
        "lower_quantile": {
            "type": "number",
            "required": False,
            "default": 0.25,
            "description": "Cuartil inferior Q1 (por defecto 0.25)",
        },
        "upper_quantile": {
            "type": "number",
            "required": False,
            "default": 0.75,
            "description": "Cuartil superior Q3 (por defecto 0.75)",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

        multiplier = parameters.get("multiplier", 1.5)
        if not isinstance(multiplier, (int, float)) or multiplier <= 0:
            raise FunctionalException(
                message="El parámetro 'multiplier' debe ser un número positivo (> 0).",
                code="INVALID_PARAMETER",
            )

        action = parameters.get("action", "cap")
        if action not in ["cap", "nullify", "drop", "flag"]:
            raise FunctionalException(
                message="El parámetro 'action' debe ser uno de: 'cap', 'nullify', 'drop', 'flag'.",
                code="INVALID_PARAMETER",
            )

        lq = parameters.get("lower_quantile", 0.25)
        uq = parameters.get("upper_quantile", 0.75)
        if not isinstance(lq, (int, float)) or not (0 < lq < 1):
            raise FunctionalException(
                message="'lower_quantile' debe ser un número entre 0 y 1.",
                code="INVALID_PARAMETER",
            )
        if not isinstance(uq, (int, float)) or not (0 < uq < 1):
            raise FunctionalException(
                message="'upper_quantile' debe ser un número entre 0 y 1.",
                code="INVALID_PARAMETER",
            )
        if lq >= uq:
            raise FunctionalException(
                message="'lower_quantile' debe ser menor que 'upper_quantile'.",
                code="INVALID_PARAMETER",
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        multiplier = float(parameters.get("multiplier", 1.5))
        action = parameters.get("action", "cap")
        lq = float(parameters.get("lower_quantile", 0.25))
        uq = float(parameters.get("upper_quantile", 0.75))

        df_copy = df.copy()
        numeric_series = pd.to_numeric(df_copy[col], errors="coerce")
        valid_values = numeric_series.dropna()

        if valid_values.empty:
            return df_copy, 0

        q1 = float(valid_values.quantile(lq))
        q3 = float(valid_values.quantile(uq))
        iqr = q3 - q1

        lower_bound = q1 - (multiplier * iqr)
        upper_bound = q3 + (multiplier * iqr)

        is_outlier = (numeric_series < lower_bound) | (numeric_series > upper_bound)
        outlier_count = int(is_outlier.sum())

        if action == "cap":
            capped = numeric_series.copy()
            capped = capped.apply(
                lambda x: (
                    lower_bound
                    if pd.notna(x) and x < lower_bound
                    else (upper_bound if pd.notna(x) and x > upper_bound else x)
                )
            )
            df_copy[col] = capped
            return df_copy, outlier_count

        elif action == "nullify":
            nullified = numeric_series.copy()
            nullified[is_outlier] = np.nan
            df_copy[col] = nullified
            return df_copy, outlier_count

        elif action == "drop":
            df_copy = df_copy[~is_outlier].reset_index(drop=True)
            return df_copy, outlier_count

        elif action == "flag":
            flag_col = f"{col}_is_outlier"
            df_copy[flag_col] = is_outlier
            return df_copy, outlier_count

        return df_copy, 0


class DetectOutliersZScoreTransformation(BaseTransformation):
    operation_name = "detect_outliers_zscore"
    description = (
        "Detecta y gestiona valores atípicos evaluando el Z-Score (|z| > threshold), "
        "con opciones para acotar (cap), anular (nullify), eliminar filas (drop) o marcar (flag)."
    )
    risk = "medium"
    reversible = False
    allowed_parameters = ["column", "threshold", "action"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Columna numérica a analizar"},
        "threshold": {
            "type": "number",
            "required": False,
            "default": 3.0,
            "description": "Umbral de Z-Score absoluto para considerar outlier (ej. 2.5 o 3.0)",
        },
        "action": {
            "type": "string",
            "required": False,
            "default": "cap",
            "enum": ["cap", "nullify", "drop", "flag"],
            "description": "Acción sobre los outliers: 'cap' (acotar límites), 'nullify' (hacer NaN), 'drop' (eliminar filas), 'flag' (crear columna booleana)",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

        threshold = parameters.get("threshold", 3.0)
        if not isinstance(threshold, (int, float)) or threshold <= 0:
            raise FunctionalException(
                message="El parámetro 'threshold' debe ser un número positivo (> 0).",
                code="INVALID_PARAMETER",
            )

        action = parameters.get("action", "cap")
        if action not in ["cap", "nullify", "drop", "flag"]:
            raise FunctionalException(
                message="El parámetro 'action' debe ser uno de: 'cap', 'nullify', 'drop', 'flag'.",
                code="INVALID_PARAMETER",
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        threshold = float(parameters.get("threshold", 3.0))
        action = parameters.get("action", "cap")

        df_copy = df.copy()
        numeric_series = pd.to_numeric(df_copy[col], errors="coerce")
        valid_values = numeric_series.dropna()

        if valid_values.empty or len(valid_values) < 2:
            if action == "flag":
                df_copy[f"{col}_is_outlier"] = False
            return df_copy, 0

        mean = float(valid_values.mean())
        std = float(valid_values.std(ddof=1))

        if std == 0 or np.isnan(std):
            # Todos los valores válidos son idénticos; no hay outliers
            if action == "flag":
                df_copy[f"{col}_is_outlier"] = False
            return df_copy, 0

        z_scores = (numeric_series - mean).abs() / std
        is_outlier = z_scores > threshold
        outlier_count = int(is_outlier.sum())

        lower_limit = mean - (threshold * std)
        upper_limit = mean + (threshold * std)

        if action == "cap":
            capped = numeric_series.copy()
            capped = capped.apply(
                lambda x: (
                    lower_limit
                    if pd.notna(x) and x < lower_limit
                    else (upper_limit if pd.notna(x) and x > upper_limit else x)
                )
            )
            df_copy[col] = capped
            return df_copy, outlier_count

        elif action == "nullify":
            nullified = numeric_series.copy()
            nullified[is_outlier] = np.nan
            df_copy[col] = nullified
            return df_copy, outlier_count

        elif action == "drop":
            df_copy = df_copy[~is_outlier].reset_index(drop=True)
            return df_copy, outlier_count

        elif action == "flag":
            flag_col = f"{col}_is_outlier"
            df_copy[flag_col] = is_outlier.fillna(False)
            return df_copy, outlier_count

        return df_copy, 0
