from pydantic import BaseModel, Field


class CacheStatsResponse(BaseModel):
    """Métricas operativas y de observabilidad de la caché de inferencia semántica (L1/L2)."""

    backend: str = Field(..., description="Backend configurado: 'memory' o 'redis'")
    distributed: bool = Field(..., description="Indica si la caché L2 distribuida está activa y disponible")
    redis_available: bool = Field(..., description="Estado de conectividad con Redis")
    redis_hits: int = Field(0, description="Aciertos en L2 (Redis distribuido)")
    redis_errors: int = Field(0, description="Errores de conexión o timeout con Redis")
    hits: int = Field(..., description="Aciertos totales de inferencia (L1 + L2)")
    l1_hits: int = Field(0, description="Aciertos en memoria local L1 (<1ms)")
    l2_hits: int = Field(0, description="Aciertos en Redis distribuido L2")
    misses: int = Field(..., description="Fallos totales de caché (requirieron llamada al LLM)")
    total_requests: int = Field(..., description="Total de consultas de inferencia evaluadas")
    hit_rate_pct: float = Field(..., description="Tasa de acierto global porcentual (%)")
    l1_hit_rate_pct: float = Field(0.0, description="Tasa de acierto de memoria L1 (%)")
    l2_hit_rate_pct: float = Field(0.0, description="Tasa de acierto de Redis L2 (%)")
    cached_entries: int = Field(..., description="Número actual de entradas almacenadas en memoria L1")
    saved_tokens: int = Field(..., description="Tokens de LLM ahorrados acumulados")
    saved_cost_usd: float = Field(..., description="Coste estimado ahorrado en USD")
