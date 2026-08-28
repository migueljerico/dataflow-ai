from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AIOperationSuggestion(BaseModel):
    operation: str = Field(..., description="Nombre de la operación del catálogo")
    column: Optional[str] = Field(None, description="Columna objetivo")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros de la transformación")
    reason: str = Field(..., description="Explicación en lenguaje claro del problema y solución sugerida")
    confidence: float = Field(default=0.9, description="Nivel de confianza de la IA (0.0 a 1.0)")
    risk: str = Field(default="low", description="Riesgo de la transformación (low, medium, high)")


class AISuggestionResponse(BaseModel):
    dataset_summary: str = Field(..., description="Resumen ejecutivo del dataset interpretado por la IA")
    suggestions: List[AIOperationSuggestion] = Field(
        default_factory=list, description="Lista de transformaciones propuestas"
    )
    warnings: List[str] = Field(default_factory=list, description="Advertencias de la IA")


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    async def suggest_transformations(
        self,
        filename: str,
        columns_schema: List[Dict[str, Any]],
        quality_issues: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]],
    ) -> AISuggestionResponse:
        """
        Envía únicamente el esquema anonimizado y problemas detectados al LLM
        para recibir sugerencias estructuradas.
        """
        pass
