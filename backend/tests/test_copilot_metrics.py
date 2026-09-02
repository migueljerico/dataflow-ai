import pytest
from app.ai_providers.base import AIMetrics, AISuggestionResponse
from app.ai_providers.mock_provider import MockProvider
from app.main import app
from app.services.ai_service import AIService
from fastapi.testclient import TestClient

client = TestClient(app)


def test_ai_metrics_model_structure():
    metrics = AIMetrics(
        latency_ms=124.5,
        prompt_tokens=350,
        completion_tokens=150,
        total_tokens=500,
        estimated_cost_usd=0.000095,
        model="gemini-2.5-flash",
        provider="gemini",
    )
    assert metrics.latency_ms == 124.5
    assert metrics.prompt_tokens == 350
    assert metrics.completion_tokens == 150
    assert metrics.total_tokens == 500
    assert metrics.estimated_cost_usd == 0.000095
    assert metrics.model == "gemini-2.5-flash"
    assert metrics.provider == "gemini"


@pytest.mark.anyio
async def test_mock_provider_generates_ai_metrics():
    provider = MockProvider()
    columns_schema = [
        {"name": "ID_Cliente", "inferred_type": "text", "semantic_hint": "id", "null_count": 0},
        {"name": "Ventas", "inferred_type": "numeric", "semantic_hint": "currency", "null_count": 1},
    ]
    quality_issues = [
        {"column": "Ventas", "dimension": "validity", "description": "Símbolos de euro en columna numérica"}
    ]
    sample_rows = [{"ID_Cliente": "CLI-001", "Ventas": "1200,50 €"}]

    res = await provider.suggest_transformations(
        filename="test_sales.csv",
        columns_schema=columns_schema,
        quality_issues=quality_issues,
        sample_rows=sample_rows,
    )

    assert isinstance(res, AISuggestionResponse)
    assert res.metrics is not None
    assert res.metrics.latency_ms >= 0.0
    assert res.metrics.prompt_tokens > 0
    assert res.metrics.completion_tokens > 0
    assert res.metrics.total_tokens == res.metrics.prompt_tokens + res.metrics.completion_tokens
    assert res.metrics.estimated_cost_usd == 0.0
    assert res.metrics.model == "mock-deterministic"
    assert res.metrics.provider == "mock"


@pytest.mark.anyio
async def test_ai_service_propose_ai_plan_includes_metrics():
    # 1. Load sample dataset
    load_res = client.post("/api/v1/datasets/samples/contact_center/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Propose plan via AI Copilot (MockProvider)
    plan = await AIService.propose_ai_plan(dataset_id, provider_name="mock")
    assert plan.ai_metrics is not None
    assert plan.ai_metrics.latency_ms >= 0.0
    assert plan.ai_metrics.total_tokens > 0
    assert plan.ai_metrics.provider == "mock"
    assert plan.ai_metrics.model == "mock-deterministic"
