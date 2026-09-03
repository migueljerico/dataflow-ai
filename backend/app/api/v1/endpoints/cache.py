from app.models.cache import CacheStatsResponse
from app.services.inference_cache import InferenceCacheService
from fastapi import APIRouter

router = APIRouter()


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Obtener estadísticas operativas y métricas de observabilidad de la caché
    de inferencia semántica (L1 memoria local + L2 Redis distribuido).
    """
    stats_dict = InferenceCacheService.get_stats()
    return CacheStatsResponse(**stats_dict)
