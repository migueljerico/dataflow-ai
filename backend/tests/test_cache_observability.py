"""
Pruebas del endpoint de observabilidad de la caché de inferencia (L1/L2).
Verifica métricas operativas, cálculo de tasas de acierto L1/L2, ahorro y persistencia.
"""

from app.ai_providers.base import AIMetrics, AISuggestionResponse
from app.main import app
from app.services.inference_cache import InferenceCacheService
from fastapi.testclient import TestClient

client = TestClient(app)


def test_get_cache_stats_endpoint_baseline():
    """Verifica que el endpoint /api/v1/cache/stats responde con la estructura completa."""
    InferenceCacheService.clear()
    res = client.get("/api/v1/cache/stats")
    assert res.status_code == 200
    data = res.json()

    assert "backend" in data
    assert "distributed" in data
    assert "redis_available" in data
    assert data["hits"] == 0
    assert data["l1_hits"] == 0
    assert data["l2_hits"] == 0
    assert data["misses"] == 0
    assert data["total_requests"] == 0
    assert data["hit_rate_pct"] == 0.0
    assert data["l1_hit_rate_pct"] == 0.0
    assert data["l2_hit_rate_pct"] == 0.0
    assert data["saved_tokens"] == 0
    assert data["saved_cost_usd"] == 0.0


def test_get_cache_stats_reflects_l1_hits_and_savings():
    """Verifica que al consultar elementos cacheados se actualizan aciertos L1 y ahorros."""
    InferenceCacheService.clear()

    # Inyectar una respuesta simulada en caché
    mock_resp = AISuggestionResponse(
        dataset_summary="Dataset de prueba para caché",
        suggestions=[],
        warnings=[],
        metrics=AIMetrics(
            latency_ms=120.0,
            prompt_tokens=500,
            completion_tokens=250,
            total_tokens=750,
            estimated_cost_usd=0.0015,
            model="gemini-2.5-flash",
            provider="gemini",
            cached=False,
        ),
    )
    test_key = "test_canonical_key_123"
    InferenceCacheService.set(test_key, mock_resp)

    # 1. Miss
    miss_res = InferenceCacheService.get("non_existent_key")
    assert miss_res is None

    # 2. Hit L1
    hit_res = InferenceCacheService.get(test_key)
    assert hit_res is not None
    assert hit_res.metrics.cached is True

    # Consultar endpoint REST
    res = client.get("/api/v1/cache/stats")
    assert res.status_code == 200
    stats = res.json()

    assert stats["total_requests"] == 2
    assert stats["hits"] == 1
    assert stats["l1_hits"] == 1
    assert stats["l2_hits"] == 0
    assert stats["misses"] == 1
    assert stats["hit_rate_pct"] == 50.0
    assert stats["l1_hit_rate_pct"] == 50.0
    assert stats["l2_hit_rate_pct"] == 0.0
    assert stats["saved_tokens"] == 750
    assert stats["saved_cost_usd"] == 0.0015
    assert stats["cached_entries"] == 1


def test_get_cache_stats_reflects_l2_redis_hits(monkeypatch):
    """Verifica que los aciertos de nivel L2 (Redis) computan métricas y tasas de acierto L2."""
    InferenceCacheService.clear()

    mock_resp = AISuggestionResponse(
        dataset_summary="Dataset L2 Redis",
        suggestions=[],
        warnings=[],
        metrics=AIMetrics(
            latency_ms=150.0,
            prompt_tokens=400,
            completion_tokens=200,
            total_tokens=600,
            estimated_cost_usd=0.0012,
            model="gemini-2.5-flash",
            provider="redis-cache",
            cached=False,
        ),
    )

    # Simular cliente Redis en _get_redis para que _redis_get ejecute su lógica real
    from unittest.mock import MagicMock
    payload = InferenceCacheService._serialize_payload(mock_resp)
    mock_redis = MagicMock()
    mock_redis.get.return_value = payload
    monkeypatch.setattr(InferenceCacheService, "_get_redis", lambda: mock_redis)

    hit_l2 = InferenceCacheService.get("key_l2_test")
    assert hit_l2 is not None
    assert hit_l2.metrics.provider == "redis-cache"

    res = client.get("/api/v1/cache/stats")
    assert res.status_code == 200
    stats = res.json()

    assert stats["total_requests"] == 1
    assert stats["hits"] == 1
    assert stats["l1_hits"] == 0
    assert stats["l2_hits"] == 1
    assert stats["misses"] == 0
    assert stats["hit_rate_pct"] == 100.0
    assert stats["l1_hit_rate_pct"] == 0.0
    assert stats["l2_hit_rate_pct"] == 100.0
    assert stats["saved_tokens"] == 600
    assert stats["saved_cost_usd"] == 0.0012

