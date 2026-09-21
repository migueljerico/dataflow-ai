"""Tests del módulo Dashboard Intelligence (v1.20.0)."""

import io

from fastapi.testclient import TestClient

from app.core import wcag
from app.main import app

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
    assert bp["dashboard_type"] in [
        "sales",
        "finance",
        "operations",
        "hr",
        "marketing",
        "inventory",
        "customers",
        "logistics",
        "academic",
        "executive",
        "generic",
    ]
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


def test_dashboard_scatter_with_continuous_numerics():
    """Regresión: el scatter con datos reales (≥30 filas, 2 numéricas continuas) no falla.

    Cubre el bug 'tuple indices must be integers or slices, not str' provocado por
    indexar filas de itertuples() por nombre de columna en _scatter_visual.
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    n = 120
    df = pd.DataFrame(
        {
            "OrderID": [f"ORD-{i:04d}" for i in range(n)],
            "CustomerID": [f"CUST-{i % 20:03d}" for i in range(n)],
            "OrderDate": pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
            "ShipCountry": rng.choice(["Spain", "France", "Germany", "Italy"], n),
            "Quantity": rng.integers(1, 50, n),
            "UnitPrice": np.round(rng.uniform(5, 200, n), 2),
            "Discount": np.round(rng.uniform(0, 0.3, n), 2),
        }
    )
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    up = client.post("/api/v1/datasets/upload", files={"file": ("big_orders.csv", buf, "text/csv")})
    assert up.status_code == 201
    ds = up.json()["dataset_id"]

    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": [ds]})
    assert res.status_code == 200, res.text[:500]
    bp = res.json()
    scatters = [v for v in bp["visuals"] if v["visual_type"] == "scatter"]
    assert len(scatters) >= 1
    assert len(scatters[0]["preview_data"]) >= 30
    first = scatters[0]["preview_data"][0]
    assert isinstance(first["value"], (int, float))
    assert isinstance(first["secondary_value"], (int, float))


# ─────────────────────────────────────────────────────────────────────────────
# Tests v2: Gobernanza de Agregación, Intención Analítica y Control de Redundancia
# ─────────────────────────────────────────────────────────────────────────────


def test_1_derived_measure_when_qty_and_price_present():
    """Test 1: La medida principal es derivada (Ventas netas) si existen cantidad y precio."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    # KPI 1 debe ser Ventas netas
    kpi1 = bp["kpis"][0]
    assert "ventas netas" in kpi1["title"].lower()
    assert kpi1["value"] is not None and kpi1["value"] > 0
    # Visuals deben referenciar ventas netas en su DAX
    for visual in bp["visuals"]:
        if visual["visual_type"] in ("line", "bar", "horizontal_bar", "donut"):
            assert "ventas_netas" in (visual.get("measure_dax") or "").lower() or "sumx" in (visual.get("measure_dax") or "").lower()


def test_2_unit_price_only_uses_average():
    """Test 2: Si solo existe precio unitario (sin cantidad), el KPI usa AVERAGE y label honesto."""
    csv_data = "ProductID,ProductName,UnitPrice\nP1,Café,15.50\nP2,Té,8.00\nP3,Galleta,4.20\n"
    buf = io.BytesIO(csv_data.encode("utf-8"))
    up = client.post("/api/v1/datasets/upload", files={"file": ("only_prices.csv", buf, "text/csv")})
    assert up.status_code == 201
    ds = up.json()["dataset_id"]

    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": [ds]})
    assert res.status_code == 200
    bp = res.json()
    kpi_main = bp["kpis"][0]
    # NUNCA SUM ni 'Total unitprice'
    assert "total" not in kpi_main["title"].lower()
    assert "medio" in kpi_main["title"].lower() or "promedio" in kpi_main["title"].lower()
    assert "average" in kpi_main["dax_formula"].lower()
    assert "sum(" not in kpi_main["dax_formula"].lower()


def test_3_aggregate_by_uses_mean_for_unit_price():
    """Test 3: Si se agrega una columna UNIT_PRICE_OR_RATE, la agregación es mean, no sum."""
    csv_data = (
        "Category,UnitPrice\n"
        "Bebidas,10.0\n"
        "Bebidas,20.0\n"
        "Comida,30.0\n"
        "Comida,50.0\n"
    )
    buf = io.BytesIO(csv_data.encode("utf-8"))
    up = client.post("/api/v1/datasets/upload", files={"file": ("categories_prices.csv", buf, "text/csv")})
    assert up.status_code == 201
    ds = up.json()["dataset_id"]

    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": [ds]})
    assert res.status_code == 200
    bp = res.json()
    bar_visuals = [v for v in bp["visuals"] if v["visual_type"] in ("bar", "horizontal_bar")]
    assert len(bar_visuals) > 0
    # Verificar que los valores agregados son promedios (Bebidas = 15.0, Comida = 40.0) y no sumas (30.0, 80.0)
    for v in bar_visuals:
        pts = {p["label"]: p["value"] for p in v["preview_data"]}
        if "Bebidas" in pts and "Comida" in pts:
            assert pts["Bebidas"] == 15.0
            assert pts["Comida"] == 40.0


def test_4_analytical_intent_populated():
    """Test 4: Cada visual tiene business_question, analytical_goal, measure_dax y priority poblados."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    valid_goals = {"evolución temporal", "comparación", "composición", "ranking", "relación", "distribución"}
    for v in bp["visuals"]:
        assert v.get("business_question"), f"Falta business_question en visual {v['visual_id']}"
        assert v.get("analytical_goal") in valid_goals, f"Objetivo analítico inválido en {v['visual_id']}"
        assert v.get("measure_dax"), f"Falta measure_dax en visual {v['visual_id']}"
        assert 1 <= v.get("priority", 0) <= 6, f"Prioridad fuera de rango en {v['visual_id']}"


def test_5_ranking_visual_horizontal_bar_descending():
    """Test 5: El visual de ranking usa horizontal_bar y sus valores están ordenados descendentemente."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    rankings = [v for v in bp["visuals"] if v.get("analytical_goal") == "ranking"]
    assert len(rankings) >= 1
    ranking = rankings[0]
    assert ranking["visual_type"] == "horizontal_bar"
    values = [p["value"] for p in ranking["preview_data"]]
    assert values == sorted(values, reverse=True)


def test_6_donut_visual_rules():
    """Test 6: Donut solo para 2..6 categorías, nunca geografía, ni dimensión ya usada en barras."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    donuts = [v for v in bp["visuals"] if v["visual_type"] == "donut"]
    bar_dims = {v["dimension"] for v in bp["visuals"] if v["visual_type"] in ("bar", "horizontal_bar") and v.get("analytical_goal") == "comparación"}
    for d in donuts:
        assert 2 <= len(d["preview_data"]) <= 6
        assert "country" not in d["dimension"].lower() and "pais" not in d["dimension"].lower()
        assert d["dimension"] not in bar_dims


def test_7_redundancy_controller_prevents_duplicates():
    """Test 7: RedundancyController previene duplicidad de dimensión con el mismo objetivo analítico."""
    from app.services.visual_engine import RedundancyController
    from app.models.dashboard import VisualTypeEnum, VisualRecommendation, ConfidenceLevelEnum, PreviewModeEnum

    rc = RedundancyController()
    assert rc.can_add("Orders[ShipCountry]", "comparación", VisualTypeEnum.BAR, category_count=4) is True

    vis = VisualRecommendation(
        visual_id="v1",
        title="Ventas por País",
        visual_type=VisualTypeEnum.BAR,
        page_id="p1",
        dimension="Orders[ShipCountry]",
        measure="[Ventas_Netas]",
        fields=["Orders[ShipCountry]"],
        reason="Test",
        confidence=ConfidenceLevelEnum.HIGH,
        confidence_rationale="Test",
        alternative_types=[],
        preview_data=[],
        preview_mode=PreviewModeEnum.REAL,
        data_quality_notes=[],
        order=0,
        analytical_goal="comparación",
    )
    rc.register(vis)

    # Misma dimensión + mismo objetivo analítico -> Prohibido
    assert rc.can_add("Orders[ShipCountry]", "comparación", VisualTypeEnum.BAR) is False
    # Donut sobre dimensión ya usada para comparación -> Prohibido
    assert rc.can_add("Orders[ShipCountry]", "composición", VisualTypeEnum.DONUT, category_count=4) is False
    # Otra dimensión diferente -> Permitido
    assert rc.can_add("Products[Category]", "comparación", VisualTypeEnum.BAR, category_count=4) is True


def test_8_no_date_no_line_visual():
    """Test 8: Si no hay columna temporal válida, jamás se genera un gráfico de líneas."""
    csv_data = "Category,Sales\nElectrónica,500\nHogar,300\nRopa,150\n"
    buf = io.BytesIO(csv_data.encode("utf-8"))
    up = client.post("/api/v1/datasets/upload", files={"file": ("no_date.csv", buf, "text/csv")})
    assert up.status_code == 201
    ds = up.json()["dataset_id"]

    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": [ds]})
    assert res.status_code == 200
    bp = res.json()
    lines = [v for v in bp["visuals"] if v["visual_type"] == "line"]
    assert len(lines) == 0


def test_9_order_count_uses_distinct_orders():
    """Test 9: El conteo de pedidos cuenta pedidos distintos (OrderID), no líneas de detalle."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    # SYNTH_DETAILS tiene 7 filas pero solo 6 OrderIDs únicos (ORD001 aparece 2 veces)
    order_kpi = next((k for k in bp["kpis"] if k["title"] == "Pedidos"), None)
    assert order_kpi is not None
    assert order_kpi["value"] == 6.0


def test_10_filter_semantic_prioritization():
    """Test 10: Los slicers se ordenan por prioridad semántica (Fecha > Geografía > Categoría)."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    filters = bp["filters"]
    assert len(filters) > 0
    # Primer filtro debe ser fecha o geografía si existen
    labels = [f["label"].lower() for f in filters]
    has_date_or_geo = any("date" in l or "fecha" in l or "country" in l or "país" in l for l in labels[:2])
    assert has_date_or_geo is True


def test_11_northwind_no_redundancy():
    """Test 11: El dataset completo no produce visuales duplicados con la misma dimensión y objetivo."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    seen = set()
    for v in bp["visuals"]:
        if v.get("dimension") and v.get("analytical_goal"):
            key = (v["dimension"], v["analytical_goal"])
            assert key not in seen, f"Visual duplicado con dimensión y objetivo: {key}"
            seen.add(key)


def test_12_wcag_palette_compliance():
    """Test 12: Cumplimiento estricto WCAG AA en todas las combinaciones clave de color."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()
    assert "PASS" in bp["design"]["accessibility"]["overall_label"]
    for pair in bp["design"]["accessibility"]["contrast_pairs"]:
        assert pair["contrast_ratio"] >= 3.0, f"Ratio {pair['contrast_ratio']} bajo en {pair['label']}"
        if pair["label"].startswith("Texto principal"):
            assert pair["aa"] is True


def test_13_unit_price_never_summed_in_dax_or_kpis():
    """Test 13: UnitPrice jamás se suma en ninguna fórmula DAX ni en ningún KPI."""
    ids = upload_and_get_ids()
    res = client.post("/api/v1/dashboard/analyze", json={"dataset_ids": ids})
    assert res.status_code == 200
    bp = res.json()

    # Comprobar KPIs
    for k in bp["kpis"]:
        formula = (k.get("dax_formula") or "").lower().replace(" ", "")
        assert "sum('order_details'[unitprice])" not in formula
        assert "sum('clean_order_details_dirty'[unitprice])" not in formula

    # Comprobar medidas DAX
    for d in bp["dax_measures"]:
        formula = (d.get("formula") or "").lower().replace(" ", "")
        assert "sum('order_details'[unitprice])" not in formula
        assert "sum('clean_order_details_dirty'[unitprice])" not in formula


def test_14_report_title_sanitizer_no_noise():
    """Test 14: ReportTitleSanitizer elimina dirty, raw, clean, .csv, guiones bajos."""
    from app.services.dashboard_service import ReportTitleSanitizer

    t1 = ReportTitleSanitizer.sanitize("Rendimiento de Ventas", "clean_order_details_dirty.csv")
    assert t1 == "Rendimiento de Ventas — Detalle de Pedidos"

    t2 = ReportTitleSanitizer.sanitize("Rendimiento de Ventas", "orders_raw.xlsx")
    assert t2 == "Rendimiento de Ventas — Pedidos"

    t3 = ReportTitleSanitizer.sanitize("Rendimiento de Ventas", "sales_dirty.csv")
    assert t3 == "Rendimiento de Ventas"

    for title in (t1, t2, t3):
        for noise in ("dirty", "raw", "clean", ".csv", ".xlsx", "_"):
            assert noise not in title.lower()

