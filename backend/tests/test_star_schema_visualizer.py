"""
Pruebas del visualizador de modelo estrella (Star Schema) para Power BI.

Verifican la inferencia de dimensiones (calendario + atributos), las relaciones
many-to-one, el script DAX de tablas calculadas, el fragmento TMDL de relaciones
y su propagación al proyecto PBIP exportado.
"""

import io
import zipfile

from app.main import app
from app.models.analytics import StarSchemaDiagram, StarSchemaDimension, StarSchemaRelationship
from app.services.analytics_service import AnalyticsService
from fastapi.testclient import TestClient

client = TestClient(app)


def _run_sales_pipeline() -> tuple[dict, str]:
    """Ejecuta el pipeline completo sobre el dataset de ventas y devuelve (guía, run_id)."""
    load_res = client.post("/api/v1/datasets/samples/sales/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()

    approve_res = client.post(
        f"/api/v1/plans/{plan_data['plan_id']}/approve", json={"steps": plan_data["steps"]}
    )
    assert approve_res.status_code == 200
    run_id = approve_res.json()["run_id"]

    analytics_res = client.get(f"/api/v1/analytics/{run_id}")
    assert analytics_res.status_code == 200
    return analytics_res.json()["integration_guide"], run_id


def test_star_schema_inference_end_to_end():
    guide, _run_id = _run_sales_pipeline()
    star = guide.get("star_schema")
    assert star is not None

    # Tabla de hechos coherente con la guía de integración
    assert star["fact_table"] == guide["table_name"]
    assert star["fact_rows"] == guide["row_count"]
    assert len(star["measures"]) >= 1

    # Dimensión calendario con DAX de tabla calculada
    dims = {d["name"]: d for d in star["dimensions"]}
    assert "Dim_Fecha" in dims
    cal = dims["Dim_Fecha"]
    assert cal["kind"] == "calendar"
    assert cal["key_column"] == "Date"
    assert "CALENDAR(" in (cal["dax_definition"] or "")
    assert "ADDCOLUMNS(" in (cal["dax_definition"] or "")
    assert "Año" in cal["suggested_attributes"]

    # Al menos una dimensión de atributo con DAX DISTINCT
    attribute_dims = [d for d in star["dimensions"] if d["kind"] == "attribute"]
    assert len(attribute_dims) >= 1
    for d in attribute_dims:
        assert "DISTINCT(" in (d["dax_definition"] or "")
        assert d["distinct_count"] >= 2

    # Relaciones many-to-one desde la tabla de hechos hacia cada dimensión
    assert star["dimension_count"] == len(star["dimensions"])
    for rel in star["relationships"]:
        assert rel["from_table"] == star["fact_table"]
        assert rel["cardinality"] == "many-to-one"
        assert rel["to_table"] in dims

    # Script DAX consolidado y fragmento TMDL de relaciones
    assert "Dim_Fecha" in star["dax_calculated_tables"]
    assert star["tmdl_relationships"] is not None
    assert "relationship " in star["tmdl_relationships"]
    assert f"fromColumn: {star['fact_table']}" in star["tmdl_relationships"]


def test_star_schema_tmdl_model_includes_relationships():
    guide, _run_id = _run_sales_pipeline()
    star_raw = guide["star_schema"]
    assert star_raw is not None

    star = StarSchemaDiagram(
        fact_table=star_raw["fact_table"],
        fact_rows=star_raw["fact_rows"],
        measures=star_raw["measures"],
        dimension_count=star_raw["dimension_count"],
        dimensions=[StarSchemaDimension(**d) for d in star_raw["dimensions"]],
        relationships=[StarSchemaRelationship(**r) for r in star_raw["relationships"]],
        dax_calculated_tables=star_raw["dax_calculated_tables"],
        tmdl_relationships=star_raw["tmdl_relationships"],
    )

    model_tmdl = AnalyticsService._build_tmdl_model_definition(
        table_name=guide["table_name"], star_schema=star
    )
    assert f"ref table '{guide['table_name']}'" in model_tmdl
    assert "relationship " in model_tmdl
    assert "fromColumn:" in model_tmdl
    assert "toColumn:" in model_tmdl
    # Cada dimensión se referencia como tabla del modelo
    for dim in star.dimensions:
        assert f"ref table '{dim.name}'" in model_tmdl


def test_star_schema_relationships_present_in_pbip_export():
    guide, run_id = _run_sales_pipeline()
    pbip_res = client.get(f"/api/v1/analytics/{run_id}/export/pbip")
    assert pbip_res.status_code == 200
    assert "application/zip" in pbip_res.headers["content-type"]

    with zipfile.ZipFile(io.BytesIO(pbip_res.content), "r") as zf:
        model_tmdl = zf.read(f"{guide['table_name']}.SemanticModel/definition/model.tmdl").decode(
            "utf-8"
        )
    assert "relationship " in model_tmdl
    assert "fromColumn:" in model_tmdl
