"""Tests del módulo Dashboard Intelligence (v1.20.0)."""

import io

import pytest
from fastapi.testclient import TestClient

from app.core import wcag
from app.main import app
from app.services.dashboard_service import DashboardService

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


def test_wcag_contrast_ratio_deterministic():
    """La fórmula de contraste WCAG es determinista y matemáticamente correcta."""
    ratio = wcag.contrast_ratio("#FFFFFF", "#000000")
    assert ratio == 21.0
    ratio2 = wcag.contrast_ratio("#000000", "#FFFFFF")
    assert ratio2 == 21.0


def test_wcag_aa_levels():
    """Los umbrales AA/AAA se aplican correctamente."""
    check = wcag.wcag_check(4.5, large_text=False)
    assert check["aa"] is True
    assert check["aaa"] is False
    check_large = wcag.wcag_check(3.0, large_text=True)
    assert check_large["aa"] is True


def test_dashboard_analyze_endpoint():
    """El endpoint /dashboard/analyze genera un Blueprint completo."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    assert bp["blueprint_id"]
    assert bp["dashboard_type"] in ["sales", "finance", "operations", "hr", "marketing", "inventory", "customers", "logistics", "academic", "executive", "generic"]
    assert len(bp["kpis"]) > 0
    assert len(bp["visuals"]) > 0
    assert bp["validation"]["status"] in ["valid", "warning", "invalid"]
    assert bp["validation"]["passed_count"] >= 15


def test_dashboard_validation_detects_invalid_fields():
    """La validación detecta campos inexistentes."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    bp = res.json()
    bp["visuals"][0]["fields"] = ["orders[ColumnaFantasma]"]
    val = client.post("/api/v1/dashboard/validate", json={"dataset_ids": ids, "blueprint": bp})
    assert val.status_code == 200
    validation = val.json()
    assert validation["status"] == "invalid"
    assert any("ColumnaFantasma" in issue for issue in validation["issues"])


def test_dashboard_wcag_palette_validated():
    """La paleta del dashboard cumple WCAG AA."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    bp = res.json()
    assert "PASS" in bp["design"]["accessibility"]["overall_label"]
    for pair in bp["design"]["accessibility"]["contrast_pairs"]:
        if pair["label"].startswith("Texto principal"):
            assert pair["aa"] is True


def test_dashboard_no_fabricated_metrics():
    """Los KPIs no referencian columnas inexistentes."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    bp = res.json()
    for kpi in bp["kpis"]:
        assert kpi["validated"] is True or kpi["value"] is None


def test_dashboard_deterministic_blueprint_id():
    """El blueprint_id es determinista para los mismos datos."""
    ids = upload_and_get_ids()
    res1 = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    res2 = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    bp1 = res1.json()
    bp2 = res2.json()
    assert bp1["blueprint_id"] == bp2["blueprint_id"]


def test_dashboard_stats_endpoint():
    """El endpoint /dashboard/stats devuelve métricas operativas."""
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "dashboard_generation_total" in stats
    assert "wcag_validation_failed" in stats
