import re
import pandas as pd
from typing import Dict, Any, Tuple
from app.transformations.base import BaseTransformation
from app.core.exceptions import FunctionalException

BUSINESS_ACRONYMS = {"SA", "S.A.", "SL", "S.L.", "SLU", "S.L.U.", "CIF", "NIF", "DNI", "IVA", "ID", "KPI", "SLA", "AHT", "CRM", "ERP", "USA", "UE", "IA", "AI"}

class TrimTextTransformation(BaseTransformation):
    operation_name = "trim_text"
    description = "Elimina espacios en blanco al inicio, final y espacios dobles consecutivos en columnas de texto."
    risk = "low"

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
    description = "Normaliza el formato de texto a Title Case (preservando siglas como SA, SL, KPI, etc.), Lowercase o Uppercase."
    risk = "low"

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        mode = parameters.get("mode", "title")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if mode not in ["title", "lower", "upper"]:
            raise FunctionalException(message=f"Modo '{mode}' no soportado. Usa 'title', 'lower' o 'upper'.", code="INVALID_PARAMETER")

    @staticmethod
    def _to_smart_title_case(val: Any) -> Any:
        if pd.isna(val) or val is None:
            return val
        s = str(val).strip()
        if not s:
            return s
        words = s.split(" ")
        formatted_words = []
        code_token_re = re.compile(r"^[A-Za-z0-9]{2,6}[-_][A-Za-z0-9]{1,}$")
        for w in words:
            clean_w = w.strip()
            upper_w = clean_w.upper()
            if upper_w in BUSINESS_ACRONYMS or code_token_re.match(clean_w):
                formatted_words.append(upper_w)
            else:
                formatted_words.append(clean_w.capitalize())
        return " ".join(formatted_words)

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

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        mappings = parameters.get("mappings")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        if not isinstance(mappings, dict) or not mappings:
            raise FunctionalException(message="Se requiere un diccionario 'mappings' con las equivalencias.", code="INVALID_PARAMETER")

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
