import io
import zipfile

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_powerbi_tmdl_and_dax_export_end_to_end():
    # 1. Load sample dataset
    load_res = client.post("/api/v1/datasets/samples/people_analytics/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    # 2. Propose & approve plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()

    approve_res = client.post(f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]})
    assert approve_res.status_code == 200
    run_id = approve_res.json()["run_id"]

    # 3. Fetch analytics report & verify integration guide structure
    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    guide = analytics_res.json()["integration_guide"]
    assert guide is not None
    assert "table_name" in guide
    assert guide["tmdl_table_definition"] is not None
    assert f"table '{guide['table_name']}'" in guide["tmdl_table_definition"]
    assert "partition" in guide["tmdl_table_definition"]
    assert "measure" in guide["tmdl_table_definition"]
    assert "column" in guide["tmdl_table_definition"]
    assert guide["dax_script"] is not None
    assert "Total_Registros" in guide["dax_script"]

    # Verify enriched multi-category Excel formulas
    excel_formulas = guide["excel_formulas"]
    assert len(excel_formulas) >= 4
    categories = {f.get("category") for f in excel_formulas}
    assert "outlier" in categories
    assert "kpi" in categories
    assert "relative" in categories
    assert "conditional" in categories
    for f in excel_formulas:
        assert f.get("target_cell") is not None
        assert f.get("formula_es").startswith("=")

    # 4. Test TMDL download endpoint
    tmdl_res = client.get(f"/api/v1/analytics/{run_id}/export/tmdl")
    assert tmdl_res.status_code == 200
    assert "text/plain" in tmdl_res.headers["content-type"]
    assert f"table '{guide['table_name']}'" in tmdl_res.text
    assert "measure 'Total_Registros'" in tmdl_res.text or "measure Total_Registros" in tmdl_res.text

    # 5. Test DAX script download endpoint
    dax_res = client.get(f"/api/v1/analytics/{run_id}/export/dax")
    assert dax_res.status_code == 200
    assert "text/plain" in dax_res.headers["content-type"]
    assert "Total_Registros" in dax_res.text
    assert "CARPETA:" in dax_res.text

    # 6. Test PBIP ZIP download endpoint
    pbip_res = client.get(f"/api/v1/analytics/{run_id}/export/pbip")
    assert pbip_res.status_code == 200
    assert "application/zip" in pbip_res.headers["content-type"]

    # Unpack and verify PBIP folder hierarchy
    zip_bytes = io.BytesIO(pbip_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert any(n.endswith(".pbip") for n in namelist)
        assert any("definition.pbidataset" in n for n in namelist)
        assert any("database.tmdl" in n for n in namelist)
        assert any("model.tmdl" in n for n in namelist)
        assert any("tables/" in n and n.endswith(".tmdl") for n in namelist)
