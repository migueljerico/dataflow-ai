import re
from typing import Any, Dict, Tuple

import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation
from app.transformations.casing import BUSINESS_ACRONYMS, smart_title_text  # noqa: F401  (re-export compatibilidad)


class TrimTextTransformation(BaseTransformation):
    operation_name = "trim_text"
    description = "Elimina espacios en blanco al inicio, final y espacios dobles consecutivos en columnas de texto."
    risk = "low"
    reversible = True
    allowed_parameters = ["column"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna de texto a limpiar"}
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        df_copy = df.copy()

        def _clean_spaces(val: Any) -> Any:
            if pd.isna(val) or val is None:
                return val
            s = str(val)
            cleaned = re.sub(r"\s+", " ", s).strip()
            return cleaned

        original_series = df_copy[col].astype(str)
        cleaned_series = df_copy[col].apply(_clean_spaces)
        affected = int((original_series != cleaned_series.astype(str)).sum())
        df_copy[col] = cleaned_series
        return df_copy, affected


class NormalizeCaseTransformation(BaseTransformation):
    operation_name = "normalize_case"
    description = (
        "Normaliza el formato de texto a Title Case (preservando siglas como SA, SL, KPI, etc.), Lowercase o Uppercase."
    )
    risk = "low"
    reversible = True
    allowed_parameters = ["column", "mode"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna a normalizar"},
        "mode": {
            "type": "string",
            "required": False,
            "default": "title",
            "enum": ["title", "lower", "upper"],
            "description": "Modo de normalización ('title', 'lower', 'upper')",
        },
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        mode = parameters.get("mode", "title")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if mode not in ["title", "lower", "upper"]:
            raise FunctionalException(
                message=f"Modo '{mode}' no soportado. Usa 'title', 'lower' o 'upper'.", code="INVALID_PARAMETER"
            )

    @staticmethod
    def _to_smart_title_case(val: Any) -> Any:
        # Delega en la lógica compartida de casing.py: preserva siglas (HR, SLU),
        # códigos (PED-201) y camelCase (DevOps) en compuestos tipo HR-California.
        return smart_title_text(val)

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        mode = parameters.get("mode", "title")
        df_copy = df.copy()

        original_series = df_copy[col].astype(str)
        if mode == "lower":
            cleaned_series = df_copy[col].astype(str).str.lower()
        elif mode == "upper":
            cleaned_series = df_copy[col].astype(str).str.upper()
        else:
            cleaned_series = df_copy[col].apply(self._to_smart_title_case)

        affected = int((original_series != cleaned_series.astype(str)).sum())
        df_copy[col] = cleaned_series
        return df_copy, affected


class NormalizeCategoryTransformation(BaseTransformation):
    operation_name = "normalize_category"
    description = "Estandariza valores categóricos mapeando variaciones a una etiqueta canónica."
    risk = "low"
    reversible = True
    allowed_parameters = ["column", "mappings"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna categórica"},
        "mappings": {
            "type": "object",
            "required": True,
            "description": "Diccionario de equivalencias {antiguo_valor: nuevo_valor}",
        },
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        mappings = parameters.get("mappings")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if not isinstance(mappings, dict) or not mappings:
            raise FunctionalException(
                message="Se requiere un diccionario 'mappings' con las equivalencias.", code="INVALID_PARAMETER"
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        mappings = parameters["mappings"]
        df_copy = df.copy()

        original_series = df_copy[col].astype(str)
        cleaned_series = df_copy[col].replace(mappings)
        affected = int((original_series != cleaned_series.astype(str)).sum())
        df_copy[col] = cleaned_series
        return df_copy, affected
