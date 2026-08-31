import io
import pandas as pd
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.number_parsing import parse_numeric_string, to_numeric_series, MISSING_MARKERS
from app.transformations.text_ops import NormalizeCaseTransformation
from app.services.profiler_service import ProfilerService
from app.models.profiling import ColumnTypeEnum, SemanticHintEnum
from app.services.quality_service import QualityService
from app.services.etl_service import ETLService

client = TestClient(app)

SAMPLE_PEDIDOS_CSV = """Fecha_Pedido,ID_Pedido,Razon_Social,Region,Unidades_Stock,Descuento_Pct,Importe_Total,Dias_Entrega,Estado_Pedido
2026-04-03,PED-201,Distribuciones Marín S.L.U.,Norte,50,10.0%,1250.00 €,3,Entregado
2026-04-03,PED-201,Distribuciones Marín S.L.U.,Norte,50,10.0%,1250.00 €,3,Entregado
05/04/2026,PED-202, TALLERES ROBLES SLU ,Sur,--,15.5%,$890.50,-2,Pendiente
2026/04/06,PED-203,Comercial Iglesias,Centro, 30 ,8.0 %,640.00 €,5,Entregado
07-04-2026,PED-204,Suministros Del Este,Norte,25,120.0%,410.00 €,1,ENVIADO
invalid_date,PED-205,ALMACENES PARDO S.L.U.,Sur,40,12.0%,975.25 €,4,entregado
2026-04-10,PED-206, Comercial Iglesias ,Centro,60,9.5%,1105.00 €,2,Entregado
2026-04-11,PED-207,Talleres Robles SLU,Sur,15,20.0%,$310.00,0,pendiente
,,,,,,,,
"""


def test_missing_markers_universal_parsing():
    """Verifica que marcadores variados (-- , ---, -, –, —, N/D, N/A, null) se convierten a None/NaN."""
    for marker in ["--", "---", "-", "–", "—", "N/D", "n/d", "N/A", "n/a", "null", "none", "nan", "  --  "]:
        parsed = parse_numeric_string(marker)
        assert parsed is None, f"El marcador '{marker}' debió convertirse a None pero dio {parsed}"

    # Valores numéricos válidos
    assert parse_numeric_string("1.250,00 €") == 1250.0
    assert parse_numeric_string("$890.50") == 890.5
    assert parse_numeric_string("15.5%") == 15.5


def test_small_sample_with_mixed_missing_markers_inferred_as_numeric():
    """Verifica que una columna pequeña con múltiples marcadores distintos (-- y N/D) se infiere como NUMERIC."""
    series = pd.Series(["50", "--", "N/D", "30", "—", "40", "15"])
    inferred_type = ProfilerService._infer_column_type(series)
    assert inferred_type == ColumnTypeEnum.NUMERIC, f"Se esperaba NUMERIC pero se infirió {inferred_type}"


def test_identifier_protection_from_normalize_case():
    """Verifica que las columnas identificadoras (ID_Pedido, Cod_Cliente, PED-201) NO son sugeridas para normalize_case."""
    df = pd.DataFrame(
        {
            "ID_Pedido": ["PED-201", "PED-202", "PED-203"],
            "Razon_Social": ["TALLERES ROBLES SLU", "ALMACENES PARDO S.L.U.", "COMERCIAL IGLESIAS"],
        }
    )

    # Verificar semantic hint
    hint_id = ProfilerService._detect_semantic_hint("ID_Pedido", df["ID_Pedido"], ColumnTypeEnum.TEXT)
    assert hint_id == SemanticHintEnum.ID

    # Verificar que el transformation _to_smart_title_case mantiene los códigos en mayúsculas
    res_id = NormalizeCaseTransformation._to_smart_title_case("PED-201")
    assert res_id == "PED-201", f"PED-201 debió mantenerse en mayúsculas pero se transformó en {res_id}"

    res_company = NormalizeCaseTransformation._to_smart_title_case("TALLERES ROBLES SLU")
    assert res_company == "Talleres Robles SLU"


def test_pedidos_dataset_end_to_end_clean():
    """Prueba integral del dataset de pedidos con Unidades_Stock con '--' y ID_Pedido con 'PED-201'."""
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("pedidos_facturacion.csv", io.BytesIO(SAMPLE_PEDIDOS_CSV.encode("utf-8")), "text/csv")},
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    # Profiling
    prof_res = client.get(f"/api/v1/datasets/{dataset_id}/profiling")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()

    # Unidades_Stock debe ser NUMERIC
    unidades_prof = next(c for c in prof_data["columns"] if c["column_name"] == "Unidades_Stock")
    assert unidades_prof["inferred_type"] == "numeric"

    # ID_Pedido debe tener hint 'id'
    id_prof = next(c for c in prof_data["columns"] if c["column_name"] == "ID_Pedido")
    assert id_prof["semantic_hint"] == "id"

    # Plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    steps = plan_data["steps"]

    # ID_Pedido NO debe tener step de normalize_case
    id_case_step = [s for s in steps if s["column"] == "ID_Pedido" and s["operation"] == "normalize_case"]
    assert len(id_case_step) == 0, "ID_Pedido no debe sufrir normalize_case"

    # Unidades_Stock SÍ debe tener convert_numeric
    stock_convert_step = [s for s in steps if s["column"] == "Unidades_Stock" and s["operation"] == "convert_numeric"]
    assert len(stock_convert_step) > 0, "Unidades_Stock debe tener convert_numeric para limpiar '--'"

    # Ejecutar Plan
    plan_id = plan_data["plan_id"]
    exec_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert exec_res.status_code == 200
    run_id = exec_res.json()["run_id"]

    # Descargar y validar CSV resultante
    dl_res = client.get(f"/api/v1/runs/{run_id}/download")
    assert dl_res.status_code == 200

    clean_df = pd.read_csv(io.StringIO(dl_res.text))

    # 1. Filas: 7 registros únicos
    assert len(clean_df) == 7

    # 2. ID_Pedido se mantiene exactamente en mayúsculas
    assert clean_df["ID_Pedido"].tolist() == [
        "PED-201",
        "PED-202",
        "PED-203",
        "PED-204",
        "PED-205",
        "PED-206",
        "PED-207",
    ]

    # 3. Unidades_Stock es numérico y la fila 2 (PED-202) es NaN/nulo
    assert pd.isna(clean_df.loc[clean_df["ID_Pedido"] == "PED-202", "Unidades_Stock"].values[0])
    valid_stocks = clean_df.loc[clean_df["ID_Pedido"] != "PED-202", "Unidades_Stock"]
    assert pd.api.types.is_numeric_dtype(clean_df["Unidades_Stock"])
    assert valid_stocks.tolist() == [50.0, 30.0, 25.0, 40.0, 60.0, 15.0]

    # 4. Razon_Social preserva siglas SLU y S.L.U.
    assert "Talleres Robles SLU" in clean_df["Razon_Social"].values
    assert "Almacenes Pardo S.L.U." in clean_df["Razon_Social"].values
    assert "Distribuciones Marín S.L.U." in clean_df["Razon_Social"].values


def test_percentage_clamp_floor_and_ceiling():
    """Verifica que columnas porcentuales acotan tanto valores negativos (<0 a 0.0) como excesos (>100 a 100.0)."""
    csv_data = """ID,Cliente,Incidencias_Pct,Descuento_Pct
1,Empresa Alfa,-2.0%,120.0%
2,Empresa Beta,15.5%,-5.0%
3,Empresa Gamma,105.0%,50.0%
4,Empresa Delta,0.0%,100.0%
"""
    upload_res = client.post(
        "/api/v1/datasets/upload", files={"file": ("test_pct.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    steps = plan_data["steps"]

    # Verificar que los pasos de clamp_range para porcentajes tienen min_value: 0.0 y max_value: 100.0
    clamp_steps = [s for s in steps if s["operation"] == "clamp_range"]
    for cs in clamp_steps:
        if cs["column"] in ["Incidencias_Pct", "Descuento_Pct"]:
            assert cs["parameters"]["min_value"] == 0.0, f"min_value en {cs['column']} debe ser 0.0"
            assert cs["parameters"]["max_value"] == 100.0, f"max_value en {cs['column']} debe ser 100.0"

    # Ejecutar
    plan_id = plan_data["plan_id"]
    exec_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert exec_res.status_code == 200
    run_id = exec_res.json()["run_id"]

    dl_res = client.get(f"/api/v1/runs/{run_id}/download")
    clean_df = pd.read_csv(io.StringIO(dl_res.text))

    # Incidencias_Pct original: [-2.0, 15.5, 105.0, 0.0] -> limpio: [0.0, 15.5, 100.0, 0.0]
    assert clean_df["Incidencias_Pct"].tolist() == [0.0, 15.5, 100.0, 0.0]

    # Descuento_Pct original: [120.0, -5.0, 50.0, 100.0] -> limpio: [100.0, 0.0, 50.0, 100.0]
    assert clean_df["Descuento_Pct"].tolist() == [100.0, 0.0, 50.0, 100.0]


def test_marketing_campaigns_dataset_no_false_percentage_clamp():
    """
    Verifica que la columna 'Conversiones' (conteos absolutos: 120, 210, 180...) NO sea clasificada
    falsamente como porcentaje ni sufra truncamiento por clamp_range [0, 100].
    """
    csv_data = """Fecha_Campana,Cod_Campana,Cliente,Canal,Presupuesto,CTR_Pct,Conversiones,Coste_Por_Lead,Estado
2026-07-01,CAM-401,Publicidad Nova S.L.,Redes Sociales,5000.00,3.2,120,12.50,Activa
2026-07-02,CAM-402,Agencia Digital S.A.,Email,2500.00,1.8,45,8.30,Activa
2026-07-03,CAM-403,Ideas Creativas S.L.,Buscadores,7500.00,4.5,210,9.75,Finalizada
2026-07-04,CAM-404,Grupo Marketing Este,Redes Sociales,3200.00,2.9,88,11.20,Activa
2026-07-05,CAM-405,Comercial Rápido S.L.,Display,1800.00,0.9,22,15.60,Pausada
2026-07-06,CAM-406,Publicidad Nova S.L.,Email,4100.00,2.1,67,10.40,Activa
2026-07-07,CAM-407,Agencia Digital S.A.,Buscadores,6300.00,5.1,180,7.90,Finalizada
2026-07-08,CAM-408,Distribuciones Vidal S.L.,Display,2900.00,1.4,39,13.10,Activa
"""
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("campanas_marketing.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    # 1. Profiling
    prof_res = client.get(f"/api/v1/datasets/{dataset_id}/profiling")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()

    conv_prof = next(c for c in prof_data["columns"] if c["column_name"] == "Conversiones")
    assert (
        conv_prof["semantic_hint"] != "percentage"
    ), f"Conversiones no debe tener hint percentage: {conv_prof['semantic_hint']}"

    ctr_prof = next(c for c in prof_data["columns"] if c["column_name"] == "CTR_Pct")
    assert ctr_prof["semantic_hint"] == "percentage", "CTR_Pct sí debe tener hint percentage"

    # 2. Plan
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    steps = plan_data["steps"]

    # Conversiones NO debe tener clamp_range
    conv_clamp_steps = [s for s in steps if s["column"] == "Conversiones" and s["operation"] == "clamp_range"]
    assert len(conv_clamp_steps) == 0, "Conversiones NO debe sufrir clamp_range"

    # 3. Ejecución y descarga
    plan_id = plan_data["plan_id"]
    exec_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert exec_res.status_code == 200
    run_id = exec_res.json()["run_id"]

    dl_res = client.get(f"/api/v1/runs/{run_id}/download")
    clean_df = pd.read_csv(io.StringIO(dl_res.text))

    # Verificar que los valores de conversiones están 100% intactos (210, 180, 120 no truncados a 100)
    assert clean_df["Conversiones"].tolist() == [120, 45, 210, 88, 22, 67, 180, 39]

    # Verificar códigos de campaña intactos
    assert clean_df["Cod_Campana"].tolist() == [
        "CAM-401",
        "CAM-402",
        "CAM-403",
        "CAM-404",
        "CAM-405",
        "CAM-406",
        "CAM-407",
        "CAM-408",
    ]
