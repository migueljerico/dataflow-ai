"""Tests de Persistencia Fase 2 (StorageBackend local/GCS) y edición HITL del Paso 5."""

import io

from fastapi.testclient import TestClient

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


def test_blueprint_persisted_to_storage_backend_after_analyze():
    """Fase 2: tras /analyze el Blueprint se serializa a JSON en el StorageBackend."""
    from app.core.storage import get_storage

    _, bp = analyze_blueprint()
    filename = blueprint_storage_name(bp["blueprint_id"])
    storage = get_storage()
    assert storage.exists(filename)
    assert b'"blueprint_id"' in storage.read_file(filename)


def test_blueprint_recovered_from_storage_after_cache_reset():
    """El Blueprint sobrevive al reciclado de la instancia (caché en memoria vacía)."""
    _, bp = analyze_blueprint()
    reset_dashboard_runtime()
    res = client.get(f"/api/v1/dashboard/{bp['blueprint_id']}")
    assert res.status_code == 200
    assert res.json()["name"] == bp["name"]
    assert res.json()["blueprint_id"] == bp["blueprint_id"]


def test_put_edits_blueprint_hitl_and_persists():
    """El usuario edita nombre, orden y visibilidad; los cambios se guardan y persisten."""
    from app.core.storage import get_storage

    ids, bp = analyze_blueprint()
    bp["name"] = "Dashboard Editado por el Usuario"
    bp["kpis"][0]["hidden"] = True
    bp["visuals"][0]["order"], bp["visuals"][1]["order"] = bp["visuals"][1]["order"], bp["visuals"][0]["order"]
    res = client.put(f"/api/v1/dashboard/{bp['blueprint_id']}", json=bp)
    assert res.status_code == 200
    saved = res.json()
    assert saved["name"] == "Dashboard Editado por el Usuario"
    assert saved["kpis"][0]["hidden"] is True
    assert saved["validation"]["status"] in ["valid", "warning", "invalid"]

    # La persistencia refleja la decisión del usuario (no la propuesta original)
    storage = get_storage()
    raw = storage.read_file(blueprint_storage_name(bp["blueprint_id"]))
    assert b"Dashboard Editado por el Usuario" in raw

    # Reciclado de instancia: la edición sobrevive
    reset_dashboard_runtime()
    res2 = client.get(f"/api/v1/dashboard/{bp['blueprint_id']}")
    assert res2.status_code == 200
    assert res2.json()["name"] == "Dashboard Editado por el Usuario"
    assert res2.json()["kpis"][0]["hidden"] is True
    assert ids  # dataset_ids conservados para futuras revalidaciones


def test_put_rejects_unknown_blueprint():
    """PUT sobre un ID inexistente devuelve 404 (no se crean Blueprints por la puerta trasera)."""
    _, bp = analyze_blueprint()
    bp["blueprint_id"] = "dbp_inexistente000000"
    res = client.put("/api/v1/dashboard/dbp_inexistente000000", json=bp)
    assert res.status_code == 404
    assert res.json()["code"] == "BLUEPRINT_NOT_FOUND"


def test_put_rejects_blueprint_id_mismatch():
    """La ruta y el cuerpo deben declarar el mismo blueprint_id."""
    _, bp = analyze_blueprint()
    res = client.put(f"/api/v1/dashboard/{bp['blueprint_id']}_otro", json=bp)
    assert res.status_code == 400
    assert res.json()["code"] == "BLUEPRINT_ID_MISMATCH"


def test_put_revalidates_edits_against_real_model():
    """Una edición que rompe la integridad se guarda pero queda marcada como invalid."""
    _, bp = analyze_blueprint()
    bp["visuals"][0]["fields"] = ["orders[ColumnaFantasma]"]
    res = client.put(f"/api/v1/dashboard/{bp['blueprint_id']}", json=bp)
    assert res.status_code == 200
    validation = res.json()["validation"]
    assert validation["status"] == "invalid"
    assert any("ColumnaFantasma" in issue for issue in validation["issues"])


def test_put_rejects_blueprint_without_datasets():
    """Sin dataset_ids no hay modelo contra el que revalidar: 400 explícito."""
    _, bp = analyze_blueprint()
    bp["dataset_ids"] = []
    res = client.put(f"/api/v1/dashboard/{bp['blueprint_id']}", json=bp)
    assert res.status_code == 400
    assert res.json()["code"] == "BLUEPRINT_DATASETS_MISSING"


def test_put_palette_switch_recomputes_wcag_pairs():
    """Al cambiar la paleta por una variante, los pares WCAG se recalculan con sus colores."""
    _, bp = analyze_blueprint()
    variants = bp["design"]["palette_variants"]
    assert len(variants) > 0, "El blueprint debe ofrecer paletas alternativas prevalidadas"
    chosen = variants[0]
    bp["design"]["palette"] = chosen
    res = client.put(f"/api/v1/dashboard/{bp['blueprint_id']}", json=bp)
    assert res.status_code == 200
    accessibility = res.json()["design"]["accessibility"]
    pairs = {p["label"]: p for p in accessibility["contrast_pairs"]}
    assert pairs["Texto principal sobre fondo"]["background"] == chosen["background_color"].upper()
    assert pairs["Texto principal sobre fondo"]["foreground"] == chosen["text_color"].upper()
    assert accessibility["overall_label"] in ("WCAG AA: PASS", "WCAG AA: FAIL")
    # La variante elegida deja de figurar como variante disponible
    names = [p["name"] for p in res.json()["design"]["palette_variants"]]
    assert chosen["name"] not in names
