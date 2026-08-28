import re
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation


class ConvertDatetimeTransformation(BaseTransformation):
    operation_name = "convert_datetime"
    description = "Convierte cadenas de fecha a ISO 8601 (%Y-%m-%d) discriminando formatos ISO y europeos y reportando fechas inválidas."
    risk = "medium"
    reversible = False
    allowed_parameters = ["column", "target_format"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Nombre de la columna de fecha a estandarizar"},
        "target_format": {
            "type": "string",
            "required": False,
            "default": "%Y-%m-%d",
            "description": "Formato de salida deseado (por defecto ISO %Y-%m-%d)",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        target_format = parameters.get("target_format", "%Y-%m-%d")
        if not isinstance(target_format, str) or not target_format.strip():
            raise FunctionalException(
                message="El parámetro 'target_format' debe ser una cadena válida.", code="INVALID_PARAMETER"
            )

    @staticmethod
    def _parse_single_date(val: Any, target_format: str) -> Tuple[Any, bool, bool]:
        """
        Retorna (formatted_val, is_valid_date, is_unparseable_invalid)
        """
        if pd.isna(val) or val is None:
            return np.nan, False, False

        s = str(val).strip()
        if not s or s.lower() in ["nan", "none", "null", ""]:
            return np.nan, False, False

        # Si es un texto claramente erróneo / corrupto
        if s.lower() in ["invalid_date", "error", "n/d", "n/a", "nd", "na"]:
            return np.nan, False, True

        # 1. Si coincide con formato ISO YYYY-MM-DD o YYYY/MM/DD
        if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", s):
            parsed = pd.to_datetime(s, dayfirst=False, errors="coerce")
            if pd.notna(parsed):
                return parsed.strftime(target_format), True, False

        # 2. Si coincide con formato europeo DD/MM/YYYY o DD-MM-YYYY
        if re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}", s):
            parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.notna(parsed):
                return parsed.strftime(target_format), True, False

        # 3. Fallback genérico para otros formatos posibles
        parsed = pd.to_datetime(s, errors="coerce")
        if pd.notna(parsed):
            return parsed.strftime(target_format), True, False

        return np.nan, False, True

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        target_format = parameters.get("target_format", "%Y-%m-%d")
        df_copy = df.copy()

        original_series = df_copy[col]
        formatted_list = []
        modified_count = 0
        invalid_count = 0
        success_count = 0

        for val in original_series:
            formatted_val, is_valid, is_invalid = self._parse_single_date(val, target_format)
            if is_valid:
                success_count += 1
            if is_invalid:
                invalid_count += 1
            if str(val).strip() != str(formatted_val):
                modified_count += 1
            formatted_list.append(formatted_val)

        # Guardar en parameters métricas para auditoría
        parameters["_audit_success_count"] = success_count
        parameters["_audit_invalid_count"] = invalid_count

        df_copy[col] = formatted_list
        return df_copy, modified_count
