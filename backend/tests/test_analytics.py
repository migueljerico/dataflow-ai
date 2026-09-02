import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_and_load_demo_sample():
    # 1. List samples
    list_res = client.get("/api/v1/datasets/samples")
    assert list_res.status_code == 200
    samples = list_res.json()
    assert len(samples) == 4
    sample_ids = [s["id"] for s in samples]
    assert "contact_center" in sample_ids
    assert "sales" in sample_ids
    assert "people_analytics" in sample_ids
    assert "logistics" in sample_ids

    # 2. Load people_analytics sample
    load_res = client.post("/api/v1/datasets/samples/people_analytics/load")
    assert load_res.status_code == 201
    meta = load_res.json()
    assert meta["filename"] == "people_analytics_corrupted.csv"
    assert meta["column_count"] == 9
    assert meta["row_count"] > 0

    # 3. Load logistics sample
    load_logistics = client.post("/api/v1/datasets/samples/logistics/load")
    assert load_logistics.status_code == 201
    meta_log = load_logistics.json()
    assert meta_log["filename"] == "logistics_pedidos_corrupted.csv"
    assert meta_log["column_count"] == 9
    assert meta_log["row_count"] > 0


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

    # 5. Validar Visualización de Clusters
    assert analytics_data["cluster_visualization"] is not None
    cluster_viz = analytics_data["cluster_visualization"]
    assert cluster_viz["total_points"] == 6
    assert len(cluster_viz["clusters"]) > 0
    assert len(cluster_viz["points"]) == 6
    assert cluster_viz["x_column"] in cluster_viz["available_numeric_columns"]
    assert cluster_viz["y_column"] in cluster_viz["available_numeric_columns"]

    # 6. Validar Visualización de Outliers (Boxplots)
    assert analytics_data["outlier_visualization"] is not None
    outlier_viz = analytics_data["outlier_visualization"]
    assert len(outlier_viz["columns"]) > 0
    for box in outlier_viz["columns"]:
        assert box["min"] <= box["q1"] <= box["median"] <= box["q3"] <= box["max"]
        assert box["lower_whisker"] <= box["upper_whisker"]
        assert box["iqr"] >= 0
    assert len(outlier_viz["scatter_points"]) == 6


def test_explicit_kmeans_and_outlier_flag_in_analytics():
    # 1. Cargar sales sample
    load_res = client.post("/api/v1/datasets/samples/sales/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Proponer y enriquecer plan con clustering explícito y detección de outliers flag
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]
    steps = plan_data["steps"]

    # Añadir paso explícito de cluster_kmeans
    steps.append(
        {
            "step_id": "step-kmeans-test",
            "operation": "cluster_kmeans",
            "column": None,
            "parameters": {"columns": ["Precio_Unidad", "Cantidad"], "n_clusters": 2, "output_column": "cluster_id"},
            "reason": "Segmentación comercial por precio y cantidad",
            "confidence": 0.95,
            "risk": "low",
            "affected_rows_estimate": 10,
            "status": "approved",
        }
    )

    # Añadir paso explícito de detect_outliers_iqr con flag
    steps.append(
        {
            "step_id": "step-outliers-flag-test",
            "operation": "detect_outliers_iqr",
            "column": "Precio_Unidad",
            "parameters": {"column": "Precio_Unidad", "multiplier": 1.5, "action": "flag"},
            "reason": "Marcar outliers de precio con columna booleana",
            "confidence": 0.95,
            "risk": "medium",
            "affected_rows_estimate": 10,
            "status": "approved",
        }
    )

    # 3. Ejecutar
    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert approve_res.status_code == 200
    run_id = approve_res.json()["run_id"]

    # 4. Obtener Analytics
    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    # Validar cluster_visualization con columna explícita
    assert data["cluster_visualization"] is not None
    assert data["cluster_visualization"]["cluster_column"] == "cluster_id"
    assert len(data["cluster_visualization"]["clusters"]) == 2

    # Validar outlier_visualization
    assert data["outlier_visualization"] is not None
    assert any(b["column"] == "Precio_Unidad" for b in data["outlier_visualization"]["columns"])


def test_export_executive_analytics_html_report():
    # 1. Cargar contact_center sample
    load_res = client.post("/api/v1/datasets/samples/contact_center/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Proponer y ejecutar plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    steps = plan_data["steps"]

    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": steps})
    assert approve_res.status_code == 200
    run_id = approve_res.json()["run_id"]

    # 3. Exportar HTML en español
    export_res = client.get(f"/api/v1/analytics/{run_id}/export?lang=es")
    assert export_res.status_code == 200
    assert "text/html" in export_res.headers["content-type"]
    assert f'filename="reporte_ejecutivo_{run_id}.html"' in export_res.headers["content-disposition"]
    html = export_res.text
    assert "<!DOCTYPE html>" in html
    assert "<svg" in html
    assert "Reporte Ejecutivo" in html
    assert "@media print" in html

    # 4. Exportar HTML en árabe (RTL)
    export_ar = client.get(f"/api/v1/analytics/{run_id}/export?lang=ar")
    assert export_ar.status_code == 200
    assert 'dir="rtl"' in export_ar.text


def test_xss_protection_and_sanitization_in_analytics_export():
    """Verifica la mitigación de la vulnerabilidad CodeQL py/reflective-xss (#10)."""
    # 1. run_id malicioso con caracteres peligrosos es bloqueado/rechazado
    bad_run_res = client.get("/api/v1/analytics/run_id<script>alert(1)</script>/export")
    assert bad_run_res.status_code in [400, 404, 422]

    bad_run_encoded = client.get("/api/v1/analytics/run_id%3Cscript%3E/export")
    assert bad_run_encoded.status_code in [400, 422]

    # 2. Con un run_id válido, lang malicioso es neutralizado y no inyecta script
    load_res = client.post("/api/v1/datasets/samples/contact_center/load")
    dataset_id = load_res.json()["dataset_id"]
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    plan_data = plan_res.json()
    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]})
    run_id = approve_res.json()["run_id"]

    xss_payload = '"><script>alert("xss")</script>'
    res = client.get(f"/api/v1/analytics/{run_id}/export?lang={xss_payload}")
    assert res.status_code == 200
    assert "<script>alert" not in res.text
    assert 'X-Content-Type-Options' in res.headers
    assert res.headers['X-Content-Type-Options'] == 'nosniff'


def test_integration_guide_in_executive_analytics_report():
    """Verifica que el reporte ejecutivo incluya la Guía de Integración adaptada para Power BI y Excel."""
    load_res = client.post("/api/v1/datasets/samples/sales/load")
    dataset_id = load_res.json()["dataset_id"]
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    plan_data = plan_res.json()
    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]})
    run_id = approve_res.json()["run_id"]

    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert "integration_guide" in data
    guide = data["integration_guide"]
    assert guide is not None
    assert "table_name" in guide
    assert "power_query_m_csv" in guide
    assert "Changed Type" in guide["power_query_m_csv"]
    assert len(guide["dax_measures"]) > 0
    assert len(guide["excel_formulas"]) > 0
    assert any("Total_Registros" in m["name"] for m in guide["dax_measures"])


def test_logistics_sample_end_to_end():
    """Verifica el flujo integral (carga, propuesta de plan, ejecución y analítica) del nuevo dataset demo de Logística."""
    # 1. Carga
    load_res = client.post("/api/v1/datasets/samples/logistics/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    assert len(plan_data["steps"]) > 0

    # 3. Aprobación y ejecución
    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]})
    assert approve_res.status_code == 200
    run_data = approve_res.json()
    assert run_data["status"] == "completed"
    assert run_data["rows_after"] > 0
    assert run_data["clean_filename"] != ""

    # 4. Analítica
    analytics_res = client.get(f"/api/v1/analytics/{run_data['run_id']}")
    assert analytics_res.status_code == 200
    assert "kpis" in analytics_res.json()
