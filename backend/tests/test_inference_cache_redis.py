"""
Pruebas de la caché de inferencia distribuida (L2 Redis / Cloud Memorystore).

Verifican el round-trip JSON entre instancias simuladas, la degradación elegante
ante caídas de Redis y el aislamiento del backend en memoria.
"""

import pytest
from app.ai_providers.base import AIMetrics, AIOperationSuggestion, AISuggestionResponse
from app.core.config import settings
from app.services.inference_cache import InferenceCacheService


class FakeRedisClient:
    """Doble de prueba de un cliente Redis con soporte de fallo controlado."""

    def __init__(self):
        self.store: dict = {}
        self.fail: bool = False

    def get(self, key: str):
        if self.fail:
            raise ConnectionError("Redis simulado caido")
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str):
        if self.fail:
            raise ConnectionError("Redis simulado caido")
        self.store[key] = value

    def scan_iter(self, match: str = None):
        return [k for k in self.store if k.startswith((match or "*").rstrip("*"))]

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


def _build_response(summary: str = "Dataset de clientes distribuido") -> AISuggestionResponse:
    return AISuggestionResponse(
        dataset_summary=summary,
        suggestions=[
            AIOperationSuggestion(
                operation="trim_text",
                column="Email",
                parameters={},
                reason="Eliminar espacios innecesarios",
            )
        ],
        warnings=[],
        metrics=AIMetrics(
            latency_ms=1900.0,
            prompt_tokens=500,
            completion_tokens=150,
            total_tokens=650,
            estimated_cost_usd=0.000112,
            model="gemini-2.5-flash",
            provider="gemini",
            cached=False,
        ),
    )


@pytest.fixture(autouse=True)
def _reset_cache_state(monkeypatch):
    """Restaura el estado global de la caché y la configuración tras cada prueba."""
    monkeypatch.setattr(settings, "INFERENCE_CACHE_BACKEND", "memory", raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", None, raising=False)
    yield
    InferenceCacheService.clear()
    InferenceCacheService.reset_runtime_state()


def test_redis_round_trip_between_simulated_instances(monkeypatch):
    """Una instancia escribe y otra instancia (L1 vacía) resuelve el hit desde Redis."""
    monkeypatch.setattr(settings, "INFERENCE_CACHE_BACKEND", "redis", raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake:6379/0", raising=False)

    fake = FakeRedisClient()
    InferenceCacheService._redis_client = fake

    key = InferenceCacheService.compute_cache_key(
        columns_schema=[{"name": "Email", "type": "string", "semantic_hint": "email"}],
        quality_issues=[],
        model="gemini-2.5-flash",
        provider="gemini",
    )

    # Instancia A: escribe en L1 + L2
    InferenceCacheService.set(key, _build_response())
    assert any(k.startswith(InferenceCacheService.KEY_PREFIX) for k in fake.store)

    # Instancia B: L1 vacía (simula otro contenedor de Cloud Run)
    InferenceCacheService._cache.clear()
    hit = InferenceCacheService.get(key)
    assert hit is not None
    assert hit.dataset_summary == "Dataset de clientes distribuido"
    assert hit.metrics.cached is True
    assert hit.metrics.total_tokens == 0
    assert hit.metrics.provider == "gemini"  # Proveedor original preservado en el hit L2

    stats = InferenceCacheService.get_stats()
    assert stats["distributed"] is True
    assert stats["redis_hits"] >= 1
    assert stats["saved_tokens"] >= 650  # Contadores globales acumulativos entre módulos
    # El hit distribuido se promueve a L1 de esta instancia
    assert stats["cached_entries"] >= 1


def test_redis_failure_degrades_gracefully_to_memory(monkeypatch):
    """Con Redis caído, set/get no lanzan excepciones y el servicio sigue operando."""
    monkeypatch.setattr(settings, "INFERENCE_CACHE_BACKEND", "redis", raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake:6379/0", raising=False)

    fake = FakeRedisClient()
    fake.fail = True
    InferenceCacheService._redis_client = fake

    key = "key_con_redis_caido"
    InferenceCacheService.set(key, _build_response())  # No debe lanzar

    hit = InferenceCacheService.get(key)  # Resuelto por L1 memoria
    assert hit is not None
    assert hit.metrics.cached is True

    stats = InferenceCacheService.get_stats()
    assert stats["redis_errors"] >= 1
    assert stats["cached_entries"] >= 1


def test_memory_backend_ignores_redis_layer(monkeypatch):
    """Con backend=memory, la capa Redis no se consulta ni se contabiliza."""
    monkeypatch.setattr(settings, "INFERENCE_CACHE_BACKEND", "memory", raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", None, raising=False)

    fake = FakeRedisClient()
    InferenceCacheService._redis_client = fake

    InferenceCacheService.set("clave_memoria", _build_response())
    assert len(fake.store) == 0  # L2 no recibe escrituras

    miss = InferenceCacheService.get("clave_inexistente")
    assert miss is None

    stats = InferenceCacheService.get_stats()
    assert stats["backend"] == "memory"
    assert stats["distributed"] is False
    assert stats["redis_hits"] == 0


def test_redis_ttl_expiration_respected(monkeypatch):
    """Las entradas de L2 con stored_at expirado se tratan como miss."""
    monkeypatch.setattr(settings, "INFERENCE_CACHE_BACKEND", "redis", raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake:6379/0", raising=False)

    fake = FakeRedisClient()
    InferenceCacheService._redis_client = fake

    key = "clave_expirable"
    InferenceCacheService.set(key, _build_response())

    # Simular almacenamiento antiguo (más allá del TTL de consulta)
    import json
    import time as _time

    raw = json.loads(fake.store[f"{InferenceCacheService.KEY_PREFIX}:{key}"])
    raw["stored_at"] = _time.time() - 99999.0
    fake.store[f"{InferenceCacheService.KEY_PREFIX}:{key}"] = json.dumps(raw)

    InferenceCacheService._cache.clear()
    assert InferenceCacheService.get(key, ttl_seconds=10.0) is None
    stats = InferenceCacheService.get_stats()
    assert stats["misses"] >= 1
    assert stats["redis_hits"] == 0
