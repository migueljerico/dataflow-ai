import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ai_copilot_plan_generation():
    csv_content = "ID,Nombre,Importe\n1, Juan , 100.50 €\n1, Juan , 100.50 €\n"
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))

    upload_res = client.post("/api/v1/datasets/upload", files={"file": ("ai_test.csv", file_bytes, "text/csv")})
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    ai_plan_res = client.post("/api/v1/plans/propose/ai", json={"dataset_id": dataset_id, "provider": "mock"})
    assert ai_plan_res.status_code == 201
    plan_data = ai_plan_res.json()

    assert "plan_id" in plan_data
    assert plan_data["source"] == "ai_copilot_mock"
    assert len(plan_data["steps"]) > 0

    # Probar ejecución del plan generado por IA
    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]})
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "completed"
