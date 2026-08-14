from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Tuple

class BaseTransformation(ABC):
    operation_name: str
    description: str
    risk: str = "low"  # "low", "medium", "high"

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
