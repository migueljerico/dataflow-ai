import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SYNTH_CUSTOMERS = (
    "CustomerID,CustomerName,City,Country\n"
    "CUST001,Empresa Alpha,Madrid,Spain\n"
    "CUST002,Beta Corp,Paris,France\n"
)

SYNTH_ORDERS = (
    "OrderID,CustomerID,OrderDate,ShipCountry\n"
    "ORD001,CUST001,2024-01-10,Spain\n"
    "ORD002,CUST002,2024-01-11,France\n"
)


def test_batch_download_zip_clean_datasets():
    # 1. Subir lote
    files = [
        ("files", ("customers.csv", io.BytesIO(SYNTH_CUSTOMERS.encode()), "text/csv")),
        ("files", ("orders.csv", io.BytesIO(SYNTH_ORDERS.encode()), "text/csv")),
    ]
    resp_up = client.post("/api/v1/datasets/upload-batch", files=files)
    assert resp_up.status_code == 201
    datasets = resp_up.json()
    assert len(datasets) == 2

    # 2. Generar y aprobar planes para ambos
    run_ids = []
    for d in datasets:
        ds_id = d["dataset_id"]
        resp_plan = client.post("/api/v1/plans/propose", json={"dataset_id": ds_id})
        assert resp_plan.status_code == 201
        plan = resp_plan.json()
        plan_id = plan["plan_id"]

        resp_exec = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": plan["steps"]})
        assert resp_exec.status_code == 200
        exec_res = resp_exec.json()
        run_ids.append(exec_res["run_id"])

    assert len(run_ids) == 2

    # 3. Descargar ZIP en lote
    run_ids_param = ",".join(run_ids)
    resp_zip = client.get(f"/api/v1/runs/batch/download-zip?run_ids={run_ids_param}")
    assert resp_zip.status_code == 200
    assert resp_zip.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in resp_zip.headers.get("content-disposition", "")

    # 4. Verificar contenido interno del ZIP
    zip_bytes = io.BytesIO(resp_zip.content)
    with zipfile.ZipFile(zip_bytes, mode="r") as zf:
        namelist = zf.namelist()
        # Debe contener CSVs limpios
        csv_entries = [n for n in namelist if n.startswith("csv/")]
        assert len(csv_entries) >= 2


def test_batch_download_zip_empty_ids():
    resp = client.get("/api/v1/runs/batch/download-zip?run_ids=")
    assert resp.status_code == 400


def test_batch_download_zip_non_existent():
    resp = client.get("/api/v1/runs/batch/download-zip?run_ids=fake_run_1,fake_run_2")
    assert resp.status_code == 404
