from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import pandas as pd


class BaseTransformation(ABC):
    operation_name: str
    description: str
    risk: str = "low"  # "low", "medium", "high"
    reversible: bool = True
    allowed_parameters: List[str] = []
    parameter_schema: Dict[str, Any] = {}
    requires_human_approval: bool = False

    def get_manifest(self) -> Dict[str, Any]:
        """Retorna el manifiesto declarativo de la transformación para el Registry."""
        return {
            "name": self.operation_name,
            "description": self.description,
            "risk": self.risk,
            "reversible": self.reversible,
            "allowed_parameters": self.allowed_parameters,
            "parameter_schema": self.parameter_schema,
            "requires_human_approval": self.requires_human_approval,
        }

    @abstractmethod
    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        """Valida que la columna exista y que los parámetros sean correctos."""
        pass

    @abstractmethod
    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        """
        Aplica la transformación sobre el DataFrame de pandas.
        Retorna una tupla: (DataFrame_modificado, número_de_filas_afectadas).
        """
        pass
