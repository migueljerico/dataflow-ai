import re
from typing import Any, Dict, Tuple

import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation
from app.transformations.casing import smart_title_text


class SplitColumnTransformation(BaseTransformation):
    operation_name = "split_column"
    description = "Divide una columna compuesta por un separador en dos columnas nuevas (ej. Department_Region → Department, Region)."
    risk = "low"
    reversible = True
    allowed_parameters = ["column", "separator", "new_columns", "keep_original"]
    parameter_schema = {
        "column": {"type": "string", "required": True, "description": "Columna origen a dividir"},
        "separator": {
            "type": "string",
            "required": False,
            "default": "-",
            "description": "Separador (por defecto '-')",
        },
        "new_columns": {
            "type": "list[string]",
            "required": False,
            "description": "Nombres de las dos columnas destino (por defecto derivados de la fuente)",
        },
        "keep_original": {
            "type": "boolean",
            "required": False,
            "default": False,
            "description": "Conservar la columna original tras la división",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if not col or col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")
        sep = parameters.get("separator", "-")
        if not isinstance(sep, str) or not sep:
            raise FunctionalException(message="El separador debe ser una cadena no vacía.", code="INVALID_PARAMETER")
        new_cols = parameters.get("new_columns")
        if new_cols is not None:
            if not isinstance(new_cols, list) or len(new_cols) != 2:
                raise FunctionalException(
                    message="'new_columns' debe ser una lista con exactamente 2 nombres de columnas.",
                    code="INVALID_PARAMETER",
                )
            for nc in new_cols:
                if not isinstance(nc, str) or not nc.strip():
                    raise FunctionalException(
                        message="Los nombres de columnas destino no pueden estar vacíos.", code="INVALID_PARAMETER"
                    )
                if nc.strip() == col:
                    raise FunctionalException(
                        message=f"El nombre destino '{nc}' coincide con la columna origen.", code="INVALID_PARAMETER"
                    )

    @staticmethod
    def _derive_new_columns(source_col: str, separator: str) -> Tuple[str, str]:
        # Department_Region + '-' → Department, Region  |  Department-Region → Department, Region
        # Si contiene '_' o '-' ya, partir por ellos
        parts = re.split(r"[-_]", source_col, maxsplit=1)
        if len(parts) == 2 and all(p.strip() for p in parts):
            return parts[0].strip(), parts[1].strip()
        # Fallback genérico
        return f"{source_col}_Part1", f"{source_col}_Part2"

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        col = parameters["column"]
        sep = parameters.get("separator", "-")
        new_cols = parameters.get("new_columns")
        keep_original = bool(parameters.get("keep_original", False))
        if not new_cols:
            new_cols = list(self._derive_new_columns(col, sep))
        col_a, col_b = new_cols[0].strip(), new_cols[1].strip()

        df_copy = df.copy()
        # Evitar sobrescribir columnas existentes que no sean la fuente
        for nc in (col_a, col_b):
            if nc in df_copy.columns and nc != col:
                raise FunctionalException(
                    message=f"La columna destino '{nc}' ya existe en el dataset.", code="COLUMN_ALREADY_EXISTS"
                )

        original_series = df_copy[col]

        # Split solo en la primera ocurrencia del separador, trim y casing inteligente
        # por segmento (preserva siglas HR y camelCase DevOps; nunca .title() crudo)
        def _split_val(val: Any) -> Tuple[Any, Any]:
            if pd.isna(val) or val is None:
                return (None, None)
            s = str(val)
            if sep not in s:
                left_t = smart_title_text(s.strip()) if s.strip() else None
                return (left_t, None)
            left, right = s.split(sep, 1)
            left_t = smart_title_text(left.strip()) if left.strip() else None
            right_t = smart_title_text(right.strip()) if right.strip() else None
            return (left_t, right_t)

        split_pairs = original_series.apply(_split_val)
        df_copy[col_a] = [p[0] for p in split_pairs]
        df_copy[col_b] = [p[1] for p in split_pairs]

        if not keep_original:
            df_copy = df_copy.drop(columns=[col])

        affected = len(df_copy)
        return df_copy, affected
