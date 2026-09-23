"""Tests del historial de Blueprints (GET /dashboard) y export TMDL/PBIP (v1.25.0)."""

import io
import json
import zipfile

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.dashboard_service import BLUEPRINT_STORAGE_PREFIX, reset_dashboard_runtime

client = TestClient(app)

SYNTH_CUSTOMERS = (
    "CustomerID,CustomerName,City,Country\n"
    "CUST001,Empresa Alpha,Madrid,Spain\n"
    "CUST002,Beta Corp,Paris,France\n"
    "CUST003,Gamma Ltd,London,United Kingdom\n"
)
SYNTH_PRODUCTS = (
    "ProductID,ProductName,CategoryID,UnitPrice\n"
    "PROD01,Café Premium,CAT01,15.50\n"
    "PROD02,Té Verde,CAT01,8.00\n"
    "PROD03,Galletas Artesanas,CAT02,4.20\n"
)
SYNTH_ORDERS = (
    "OrderID,CustomerID,OrderDate,ShipCountry\n"
    "ORD001,CUST001,2024-01-10,Spain\n"
    "ORD002,CUST002,2024-01-11,France\n"
    "ORD003,CUST001,2024-01-12,Spain\n"
    "ORD004,CUST003,2024-01-13,United Kingdom\n"
    "ORD005,CUST002,2024-01-14,France\n"
    "ORD006,CUST001,2024-01-15,Spain\n"
)
SYNTH_DETAILS = (
    "OrderDetailID,OrderID,ProductID,Quantity,UnitPrice,Discount\n"
    "DET001,ORD001,PROD01,5,15.50,0.05\n"
    "DET002,ORD001,PROD02,10,8.00,0.00\n"
    "DET003,ORD002,PROD01,2,15.50,0.10\n"
    "DET004,ORD003,PROD03,20,4.20,0.15\n"
    "DET005,ORD004,PROD01,7,15.50,0.00\n"
    "DET006,ORD005,PROD02,12,8.00,0.05\n"
    "DET007,ORD006,PROD03,9,4.20,0.00\n"
)


def upload_and_get_ids():
    files = [
        ("files", ("customers.csv", io.BytesIO(SYNTH_CUSTOMERS.encode()), "text/csv")),
        ("files", ("products.csv", io.BytesIO(SYNTH_PRODUCTS.encode()), "text/csv")),
        ("files", ("orders.csv", io.BytesIO(SYNTH_ORDERS.encode()), "text/csv")),
        ("files", ("order_details.csv", io.BytesIO(SYNTH_DETAILS.encode()), "text/csv")),
    ]
    up = client.post("/api/v1/datasets/upload-batch", files=files)
    assert up.status_code == 201
    return [d["dataset_id"] for d in up.json()]


def analyze_blueprint():
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    return ids, res.json()


def blueprint_storage_name(blueprint_id: str) -> str:
    return f"{BLUEPRINT_STORAGE_PREFIX}{blueprint_id}.json"


def _history_ids():
    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == len(body["items"])
    assert body["retention_days"] == settings.BLUEPRINT_RETENTION_DAYS
    return body, [item["blueprint_id"] for item in body["items"]]


def test_history_endpoint_lists_summary_with_retention():
    """GET /dashboard devuelve resúmenes ligeros del historial (Paso 5)."""
    _, bp = analyze_blueprint()
    body, ids = _history_ids()
    assert bp["blueprint_id"] in ids

    item = next(i for i in body["items"] if i["blueprint_id"] == bp["blueprint_id"])
    assert item["name"] == bp["name"]
    assert item["dashboard_type"] == bp["dashboard_type"]
    assert item["dataset_ids"] == bp["dataset_ids"]
    assert item["kpi_count"] == len(bp["kpis"])
    assert item["visual_count"] == len(bp["visuals"])
    assert item["palette_name"] == bp["design"]["palette"]["name"]
    assert item["validation_status"] in ("valid", "warning", "invalid", None)
    assert item["created_at"]

    # El resumen no arrastra datos pesados del preview
    assert "preview_data" not in item
    assert "pages" not in item


def test_history_survives_cache_reset():
    """El historial se reconstruye desde el StorageBackend (reciclado de instancia)."""
    _, bp = analyze_blueprint()
    reset_dashboard_runtime()
    _, ids = _history_ids()
    assert bp["blueprint_id"] in ids
    assert client.get(f"/api/v1/dashboard/{bp['blueprint_id']}").status_code == 200


def test_history_ttl_hides_and_purges_expired_blueprints():
    """La retención (TTL) excluye del historial y purga el artefacto caducado."""
    from app.core.storage import get_storage

    assert settings.BLUEPRINT_RETENTION_DAYS > 0, "el TTL debe estar activo por defecto"
    _, bp = analyze_blueprint()
    filename = blueprint_storage_name(bp["blueprint_id"])
    storage = get_storage()

    payload = json.loads(storage.read_file(filename))
    payload["created_at"] = "2020-01-01T00:00:00+00:00"
    storage.save_file(filename, json.dumps(payload).encode("utf-8"))
    reset_dashboard_runtime()

    _, ids = _history_ids()
    assert bp["blueprint_id"] not in ids
    assert not storage.exists(filename), "la retención debe purgar el JSON caducado"
    assert client.get(f"/api/v1/dashboard/{bp['blueprint_id']}").status_code == 404


def test_history_retention_zero_disables_ttl(monkeypatch):
    """BLUEPRINT_RETENTION_DAYS=0 desactiva el TTL: nada se oculta ni se purga."""
    from app.core.storage import get_storage

    monkeypatch.setattr(settings, "BLUEPRINT_RETENTION_DAYS", 0)
    _, bp = analyze_blueprint()
    filename = blueprint_storage_name(bp["blueprint_id"])
    storage = get_storage()

    payload = json.loads(storage.read_file(filename))
    payload["created_at"] = "2020-01-01T00:00:00+00:00"
    storage.save_file(filename, json.dumps(payload).encode("utf-8"))
    reset_dashboard_runtime()

    _, ids = _history_ids()
    assert bp["blueprint_id"] in ids
    assert storage.exists(filename)
    assert client.get(f"/api/v1/dashboard/{bp['blueprint_id']}").status_code == 200


def test_export_tmdl_returns_model_tables_and_measures():
    """GET /dashboard/{id}/export/tmdl entrega el script TMDL completo."""
    _, bp = analyze_blueprint()
    res = client.get(f"/api/v1/dashboard/{bp['blueprint_id']}/export/tmdl")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert f'blueprint_{bp["blueprint_id"]}.tmdl' in res.headers["content-disposition"]

    body = res.text
    assert "model Model" in body
    assert "ref table '" in body
    assert "table '" in body
    first_measure = bp["dax_measures"][0]["name"]
    assert f"measure '{first_measure}'" in body
    # Fuente real de los datasets y columna calculada determinista del pipeline
    assert "Csv.Document(File.Contents(" in body
    assert "partition '" in body
    assert "__ventas_netas" in body


def test_export_pbip_returns_project_zip():
    """GET /dashboard/{id}/export/pbip entrega el proyecto .pbip completo."""
    _, bp = analyze_blueprint()
    res = client.get(f"/api/v1/dashboard/{bp['blueprint_id']}/export/pbip")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert ".pbip.zip" in res.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        names = zf.namelist()
        assert len([n for n in names if n.endswith(".pbip")]) == 1
        assert any(n.endswith(".SemanticModel/definition.pbidataset") for n in names)
        assert any(n.endswith(".SemanticModel/diagramLayout.json") for n in names)
        assert any(n.endswith("definition/database.tmdl") for n in names)
        assert any(n.endswith("definition/cultures/es-ES.tmdl") for n in names)

        model_path = next(n for n in names if n.endswith("definition/model.tmdl"))
        assert "model Model" in zf.read(model_path).decode("utf-8")

        table_files = [n for n in names if "/definition/tables/" in n]
        assert table_files
        joined = b"".join(zf.read(n) for n in table_files)
        assert b"measure '" in joined
        assert b"partition '" in joined


def test_export_endpoints_return_404_for_unknown_blueprint():
    """No se exporta nada de un Blueprint inexistente (sin artefactos fantasma)."""
    for suffix in ("tmdl", "pbip"):
        res = client.get(f"/api/v1/dashboard/dbp_inexistente000000/export/{suffix}")
        assert res.status_code == 404
        assert res.json()["code"] == "BLUEPRINT_NOT_FOUND"
