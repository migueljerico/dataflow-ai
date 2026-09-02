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


class AIMetrics(BaseModel):
    latency_ms: float = Field(default=0.0, description="Latencia de inferencia en milisegundos")
    prompt_tokens: int = Field(default=0, description="Tokens consumidos en el prompt de entrada")
    completion_tokens: int = Field(default=0, description="Tokens generados en la respuesta")
    total_tokens: int = Field(default=0, description="Total de tokens consumidos")
    estimated_cost_usd: float = Field(default=0.0, description="Coste estimado en dólares estadounidenses (USD)")
    model: str = Field(default="", description="Identificador del modelo empleado")
    provider: str = Field(default="", description="Nombre del proveedor (gemini, mock, etc.)")
    cached: bool = Field(default=False, description="Indica si la respuesta fue servida desde la caché de inferencia")


class AISuggestionResponse(BaseModel):
    dataset_summary: str = Field(..., description="Resumen ejecutivo del dataset interpretado por la IA")
    suggestions: List[AIOperationSuggestion] = Field(
        default_factory=list, description="Lista de transformaciones propuestas"
    )
    warnings: List[str] = Field(default_factory=list, description="Advertencias de la IA")
    metrics: Optional[AIMetrics] = Field(
        None, description="Métricas de observabilidad de la inferencia (latencia, tokens, costes)"
    )


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
