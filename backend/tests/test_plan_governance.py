"""
Tests de gobierno del pipeline: los planes inexistentes deben fallar con 404
en lugar de ejecutarse silenciosamente contra datasets arbitrarios.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_unknown_plan_returns_404():
    res = client.get("/api/v1/plans/PLAN-NOEXISTE")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "PLAN_NOT_FOUND"


def test_approve_unknown_plan_returns_404_without_executing():
    res = client.post(
        "/api/v1/plans/PLAN-NOEXISTE/approve",
        json={"steps": []},
    )
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "PLAN_NOT_FOUND"
