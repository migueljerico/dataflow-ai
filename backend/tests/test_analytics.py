import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_and_load_demo_sample():
    # 1. List samples
    list_res = client.get("/api/v1/datasets/samples")
    assert list_res.status_code == 200
    samples = list_res.json()
    assert len(samples) == 3
    sample_ids = [s["id"] for s in samples]
    assert "contact_center" in sample_ids
    assert "sales" in sample_ids
    assert "people_analytics" in sample_ids

    # 2. Load people_analytics sample
    load_res = client.post("/api/v1/datasets/samples/people_analytics/load")
    assert load_res.status_code == 201
    meta = load_res.json()
    assert meta["filename"] == "people_analytics_corrupted.csv"
    assert meta["column_count"] == 9
    assert meta["row_count"] > 0

def test_people_analytics_end_to_end_and_business_insights():
    # 1. Load sample
    load_res = client.post("/api/v1/datasets/samples/people_analytics/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Propose Plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]
    steps = plan_data["steps"]

    # Validar que las transformaciones semánticas están presentes
    op_map = {(s.get("column") or "global", s["operation"]): s for s in steps}
    assert ("Nombre_Empleado", "normalize_case") in op_map
    assert ("Horas_Mes", "convert_numeric") in op_map
    assert ("Productividad_Pct", "clamp_range") in op_map
    assert ("Absentismo_Dias", "clamp_range") in op_map

    # 3. Execute Plan
    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert approve_res.status_code == 200
    run_data = approve_res.json()
    run_id = run_data["run_id"]
    assert run_data["rows_after"] == 6  # 8 datos - 1 vacía - 1 dup = 6

    # 4. Request Business Analytics
    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    assert analytics_data["domain"] == "people_analytics"
    
    kpis = {k["id"]: k for k in analytics_data["kpis"]}
    # Productividad media real con clamp a 100% (88.2% - 88.3% vs 90.2% sin clamp)
    assert kpis["kpi-avg-prod"]["numeric_value"] in [88.2, 88.3]
    # Absentismo acumulado real con clamp a 0 (3 días vs 0 días con -3 cancelando)
    assert kpis["kpi-total-abs"]["numeric_value"] == 3.0
    assert "3 días" in kpis["kpi-total-abs"]["value"]
