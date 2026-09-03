from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runs_history_and_quality_comparison_flow():
    # 1. Cargar dataset demo
    res_load = client.post("/api/v1/datasets/samples/sales/load")
    assert res_load.status_code == 201
    dataset = res_load.json()
    dataset_id = dataset["dataset_id"]

    # 2. Generar plan ETL
    res_plan = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert res_plan.status_code == 201
    plan = res_plan.json()
    plan_id = plan["plan_id"]
    steps = plan["steps"]

    # 3. Ejecutar plan ETL
    res_exec = client.post(
        f"/api/v1/plans/{plan_id}/approve",
        json={"steps": steps},
    )
    assert res_exec.status_code == 200
    run_data = res_exec.json()
    run_id = run_data["run_id"]

    # 4. Comprobar endpoint de reporte con score_before y score_after
    res_rep = client.get(f"/api/v1/runs/{run_id}/report")
    assert res_rep.status_code == 200
    report_json = res_rep.json()
    assert "score_before" in report_json
    assert "score_after" in report_json
    assert "score_delta" in report_json
    assert report_json["score_after"] >= report_json["score_before"]

    # 5. Comprobar endpoint de comparativa de calidad detallada
    res_comp = client.get(f"/api/v1/runs/{run_id}/quality-comparison")
    assert res_comp.status_code == 200
    comp_json = res_comp.json()
    assert comp_json["run_id"] == run_id
    assert len(comp_json["dimensions"]) == 5
    assert comp_json["delta_score"] >= 0
    assert "explanation" in comp_json

    # 6. Comprobar endpoint de listado de historial de runs
    res_history = client.get("/api/v1/runs/")
    assert res_history.status_code == 200
    history_json = res_history.json()
    assert isinstance(history_json, list)
    assert len(history_json) >= 1
    target_run = next(r for r in history_json if r["run_id"] == run_id)
    assert target_run["applied_steps_count"] == len(steps)
    assert target_run["score_after"] >= target_run["score_before"]

    # 7. Comprobar filtrado por dataset_id
    res_filtered = client.get(f"/api/v1/runs/?dataset_id={dataset_id}")
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()) >= 1

    # 8. Comprobar comparativa entre dos ejecuciones
    res_two = client.get(f"/api/v1/runs/compare?run_a={run_id}&run_b={run_id}")
    assert res_two.status_code == 200
    two_json = res_two.json()
    assert two_json["delta_score"] == 0.0

    # 9. Comprobar analytics con drift_analysis integrado
    res_analytics = client.get(f"/api/v1/analytics/{run_id}")
    assert res_analytics.status_code == 200
    analytics_json = res_analytics.json()
    assert "drift_analysis" in analytics_json
    assert analytics_json["drift_analysis"] is not None
    assert "overall_drift_status" in analytics_json["drift_analysis"]
    assert "columns" in analytics_json["drift_analysis"]
