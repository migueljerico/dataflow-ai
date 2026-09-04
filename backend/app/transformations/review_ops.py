from typing import Any, Dict, Tuple

import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation


class FlagForReviewTransformation(BaseTransformation):
    operation_name = "flag_for_review"
    description = (
        "Marca registros para revisión humana sin modificar datos: no altera valores, "
        "solo deja constancia auditable de la incidencia detectada."
    )
    risk = "high"
    reversible = True
    allowed_parameters = ["column", "context"]
    parameter_schema = {
        "column": {
            "type": "string",
            "required": False,
            "description": "Columna afectada (opcional si el marcaje es global)",
        },
        "context": {
            "type": "object",
            "required": False,
            "description": "Contexto de la incidencia (condición, conteo, rango, estrategia sugerida)",
        },
    }
    requires_human_approval = True

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        col = parameters.get("column")
        if col is not None and col not in df.columns:
            raise FunctionalException(message=f"La columna '{col}' no existe en el dataset.", code="INVALID_COLUMN")

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        df_copy = df.copy()
        col = parameters.get("column")
        if col is None or col not in df_copy.columns:
            return df_copy, 0
        affected = int(df_copy[col].isna().sum())
        return df_copy, affected
