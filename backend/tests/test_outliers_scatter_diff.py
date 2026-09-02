import pandas as pd
from app.main import app
from app.services.analytics_service import AnalyticsService
from fastapi.testclient import TestClient

client = TestClient(app)


def test_build_outlier_visualization_scatter_diff():
    # Dataset Crudo con outliers evidentes
    raw_df = pd.DataFrame(
        {
            "AHT": [300, 320, -150, 400, 950, 310, 330, 305],
            "Agente": [f"Agente {i}" for i in range(1, 9)],
        }
    )

    # Dataset Limpio tras clamp_range [0, 600]
    clean_df = pd.DataFrame(
        {
            "AHT": [300.0, 320.0, 0.0, 400.0, 600.0, 310.0, 330.0, 305.0],
            "Agente": [f"Agente {i}" for i in range(1, 9)],
        }
    )

    viz = AnalyticsService._build_outlier_visualization(clean_df, raw_df=raw_df)
    assert viz is not None
    assert viz.active_column == "AHT"
    assert viz.diff_summary is not None
    assert viz.diff_summary.raw_outliers_count >= 1
    assert viz.scatter_points is not None
    assert len(viz.scatter_points) == 8

    # Verificar que el punto con -150 en crudo y 0.0 en limpio tiene trazabilidad diff
    mod_points = [p for p in viz.scatter_points if p.was_modified]
    assert len(mod_points) >= 1
    clamped_point = next(p for p in mod_points if p.row_index == 2)
    assert clamped_point.y_value == 0.0
    assert clamped_point.raw_y_value == -150.0
    assert clamped_point.was_modified is True
    assert clamped_point.diff_status in ["clamped", "resolved_outlier"]


def test_outlier_scatter_diff_end_to_end_analytics_endpoint():
    # 1. Load sample dataset people_analytics
    load_res = client.post("/api/v1/datasets/samples/people_analytics/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Propose Plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]
    steps = plan_data["steps"]

    # 3. Execute Plan
    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert approve_res.status_code == 200
    run_id = approve_res.json()["run_id"]

    # 4. Fetch Analytics Report and inspect Outlier Diff
    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    report = analytics_res.json()

    assert report["outlier_visualization"] is not None
    outlier_viz = report["outlier_visualization"]
    assert "scatter_points" in outlier_viz
    assert len(outlier_viz["scatter_points"]) > 0

    # Validar que los campos del comparador diff están presentes
    first_pt = outlier_viz["scatter_points"][0]
    assert "was_modified" in first_pt
    assert "diff_status" in first_pt
