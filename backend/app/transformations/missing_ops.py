from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation


class FillMissingTransformation(BaseTransformation):
    operation_name = "fill_missing"
    description = "Imputa valores nulos mediante constante, media, mediana o moda."
    risk = "medium"
    reversible = False
    allowed_parameters = ["column", "strategy", "value"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna a imputar"},
        "strategy": {
            "type": "string",
            "required": False,
            "default": "constant",
            "enum": ["constant", "mean", "median", "mode"],
            "description": "Estrategia de imputación",
        },
        "value": {
            "type": "any",
            "required": False,
            "default": "Desconocido",
            "description": "Valor constante si strategy=constant",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        strategy = parameters.get("strategy", "constant")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if strategy not in ["constant", "mean", "median", "mode"]:
            raise FunctionalException(
                message=f"Estrategia de imputación '{strategy}' no soportada. Usa 'constant', 'mean', 'median' o 'mode'.",
                code="INVALID_PARAMETER",
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        strategy = parameters.get("strategy", "constant")
        val = parameters.get("value", "Desconocido")
        df_copy = df.copy()

        # Reemplazar cadenas vacías por NaN para que pandas.isna() las detecte
        df_copy[col] = df_copy[col].replace(r"^\s*$", np.nan, regex=True)
        series = df_copy[col]
        null_mask = series.isna()
        affected = int(null_mask.sum())

        if affected == 0:
            return df_copy, 0

        if strategy == "mean":
            fill_val = pd.to_numeric(series, errors="coerce").mean()
        elif strategy == "median":
            fill_val = pd.to_numeric(series, errors="coerce").median()
        elif strategy == "mode":
            mode_series = series.mode()
            fill_val = mode_series.iloc[0] if len(mode_series) > 0 else val
        else:
            fill_val = val

        df_copy[col] = series.fillna(fill_val)
        return df_copy, affected


class RemoveDuplicatesTransformation(BaseTransformation):
    operation_name = "remove_duplicates"
    description = "Elimina filas duplicadas exactas o basadas en columnas específicas."
    risk = "high"
    reversible = False
    allowed_parameters = ["subset_columns"]
    parameter_schema = {
        "subset_columns": {
            "type": "list[string]",
            "required": False,
            "description": "Lista de columnas clave o vacía para todas las columnas",
        }
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        subset = parameters.get("subset_columns")
        if subset:
            if not isinstance(subset, list):
                raise FunctionalException(
                    message="El parámetro 'subset_columns' debe ser una lista de nombres de columnas.",
                    code="INVALID_PARAMETER",
                )
            for col in subset:
                if col not in df.columns:
                    raise FunctionalException(
                        message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN"
                    )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        subset = parameters.get("subset_columns")
        df_copy = df.copy()

        before_count = len(df_copy)
        df_cleaned = df_copy.drop_duplicates(subset=subset, keep="first")
        after_count = len(df_cleaned)

        affected = before_count - after_count
        return df_cleaned, affected


class RenameColumnTransformation(BaseTransformation):
    operation_name = "rename_column"
    description = "Renombra una columna existente del dataset."
    risk = "low"
    reversible = True
    allowed_parameters = ["column", "new_name"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre actual de la columna"},
        "new_name": {"type": "string", "required": True, "description": "Nuevo nombre deseado"},
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        new_name = parameters.get("new_name")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if not new_name or not isinstance(new_name, str) or not new_name.strip():
            raise FunctionalException(
                message="Se requiere un nuevo nombre de columna válido.", code="INVALID_PARAMETER"
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        new_name = parameters["new_name"].strip()
        df_copy = df.copy()

        df_copy = df_copy.rename(columns={col: new_name})
        return df_copy, len(df_copy)


class DropColumnTransformation(BaseTransformation):
    operation_name = "drop_column"
    description = "Elimina una columna redundante o no deseada del dataset."
    risk = "high"
    reversible = False
    allowed_parameters = ["column"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna a eliminar"}
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if len(df.columns) <= 1:
            raise FunctionalException(
                message="No se puede eliminar la única columna del dataset.", code="INVALID_OPERATION"
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        df_copy = df.copy()

        df_copy = df_copy.drop(columns=[col])
        return df_copy, len(df_copy)
