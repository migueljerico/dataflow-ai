import time

import pytest
from app.ai_providers.base import AIMetrics, AIOperationSuggestion, AISuggestionResponse
from app.main import app
from app.services.ai_service import AIService
from app.services.inference_cache import InferenceCacheService
from fastapi.testclient import TestClient

client = TestClient(app)


def test_inference_cache_canonical_key_generation():
    # Mismos campos y tipos en distinto orden deben producir exactamente el mismo hash canónico
    cols_a = [
        {"name": "Edad", "type": "int", "semantic_hint": "numeric"},
        {"name": "Email", "type": "string", "semantic_hint": "email"},
    ]
    cols_b = [
        {"name": "Email", "type": "string", "semantic_hint": "email"},
        {"name": "Edad", "type": "int", "semantic_hint": "numeric"},
    ]
    issues = [{"column": "Email", "dimension": "validity", "severity": "medium"}]

    key_a = InferenceCacheService.compute_cache_key(cols_a, issues, model="gemini-2.5-flash", provider="gemini")
    key_b = InferenceCacheService.compute_cache_key(cols_b, issues, model="gemini-2.5-flash", provider="gemini")

    assert key_a == key_b
    assert len(key_a) == 64  # SHA-256 hex


def test_inference_cache_hit_and_savings_tracking():
    InferenceCacheService.clear()

    key = "test_key_123"
    metrics = AIMetrics(
        latency_ms=1850.0,
        prompt_tokens=450,
        completion_tokens=120,
        total_tokens=570,
        estimated_cost_usd=0.000093,
        model="gemini-2.5-flash",
        provider="gemini",
        cached=False,
    )
    resp = AISuggestionResponse(
        dataset_summary="Dataset de prueba de clientes",
        suggestions=[
            AIOperationSuggestion(
                operation="trim_text",
                column="Email",
                parameters={},
                reason="Eliminar espacios innecesarios",
            )
        ],
        warnings=[],
        metrics=metrics,
    )

    # Inicialmente debe ser un miss
    assert InferenceCacheService.get(key) is None
    stats = InferenceCacheService.get_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Guardar en cache
    InferenceCacheService.set(key, resp)

    # Segundo acceso: debe ser un hit
    hit_resp = InferenceCacheService.get(key)
    assert hit_resp is not None
    assert hit_resp.dataset_summary == "Dataset de prueba de clientes"
    assert hit_resp.metrics.cached is True
    assert hit_resp.metrics.estimated_cost_usd == 0.0
    assert hit_resp.metrics.total_tokens == 0
    assert hit_resp.metrics.latency_ms < 5.0

    stats_after = InferenceCacheService.get_stats()
    assert stats_after["hits"] == 1
    assert stats_after["saved_tokens"] == 570
    assert stats_after["saved_cost_usd"] == 0.000093


def test_inference_cache_ttl_expiration():
    InferenceCacheService.clear()
    key = "expiring_key"
    resp = AISuggestionResponse(
        dataset_summary="Dataset temporal",
        suggestions=[],
        warnings=[],
        metrics=AIMetrics(model="test"),
    )

    InferenceCacheService.set(key, resp)
    # TTL de 0.05s
    hit_immediately = InferenceCacheService.get(key, ttl_seconds=10.0)
    assert hit_immediately is not None

    time.sleep(0.06)
    expired_lookup = InferenceCacheService.get(key, ttl_seconds=0.05)
    assert expired_lookup is None


@pytest.mark.anyio
async def test_ai_service_propose_ai_plan_with_cache():
    InferenceCacheService.clear()

    # 1. Cargar dataset sample
    load_res = client.post("/api/v1/datasets/samples/sales/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Primera llamada (cache miss): debe invocar el mock provider y cachear
    plan_1 = await AIService.propose_ai_plan(dataset_id=dataset_id, provider_name="mock")
    assert plan_1.ai_metrics is not None
    assert plan_1.ai_metrics.cached is False

    stats_1 = InferenceCacheService.get_stats()
    assert stats_1["cached_entries"] >= 1
    assert stats_1["misses"] >= 1

    # 3. Segunda llamada (cache hit): debe resolverse desde la caché de inferencia
    plan_2 = await AIService.propose_ai_plan(dataset_id=dataset_id, provider_name="mock")
    assert plan_2.ai_metrics is not None
    assert plan_2.ai_metrics.cached is True
    assert plan_2.ai_metrics.estimated_cost_usd == 0.0
    assert len(plan_2.steps) == len(plan_1.steps)

    stats_2 = InferenceCacheService.get_stats()
    assert stats_2["hits"] >= 1
