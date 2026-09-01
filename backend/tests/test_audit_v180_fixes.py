import io
import pytest
import pandas as pd

from app.core.exceptions import FunctionalException
from app.core.number_parsing import (
    get_numeric_parseable_ratio,
    is_missing_series,
    is_missing_value,
    to_numeric_series,
)
from app.core.semantics import is_id_or_code_column, is_percentage_or_score_column
from app.models.etl import StepStatusEnum, TransformationStep
from app.models.profiling import ColumnTypeEnum, SemanticHintEnum
from app.services.ai_service import AIService
from app.services.dataset_service import DatasetService
from app.services.etl_service import ETLService
from app.services.profiler_service import ProfilerService
from app.services.quality_service import QualityService
from app.transformations.numeric_ops import ClampRangeTransformation, ConvertNumericTransformation

SAMPLE_CSV_CONTENT = """ID_Cliente;ID_Pedido;Empresa;CIF;Fecha_Alta;Region;Codigo_Postal;Ingresos_Anuales;Conversiones;Visitas_Web;Tasa_Conversion_Pct;Descuento_Pct;Score_Calidad;Gasto_Medio_Mensual;Frecuencia_Compra_Mensual;Unidades_Stock;Segmento;Observaciones
CLI-001;PED-201;Distribuciones Ibéricas SL;B12345678;15/03/2023;Aragón;50001;125.430,50 €;95;3200;68,50%;12,00%;88;2450,75;15;120;Premium;
CLI-002;PED-202;Tecnología Aragonesa SA;A87654321;22/07/2022;Aragón;50002;198.700,00 €;210;5400;74,20%;8,50%;92;3100,20;18;85;Premium;
CLI-003;PED-203;Consultora Zaragoza SLU;B23456789;03/11/2024;Aragón;50003;156.200,25 €;180;4100;71,00%;10,00%;90;2800,00;16;--;Premium;
CLI-004;PED-204;Grupo Industrial Ebro SA;A34567890;19/01/2023;Aragón;50018;210.500,80 €;225;6200;79,80%;5,00%;95;3350,50;19;60;Premium;Cliente estratégico
CLI-005;PED-205;Logística del Norte SL;B45678901;08/09/2024;Navarra;31001;178.900,00 €;198;4800;76,40%;7,50%;93;2950,30;17;n/d;Premium;
CLI-006;PED-206;Servicios Financieros Huesca SA;A56789012;27/04/2022;Aragón;22001;165.300,60 €;175;3900;72,90%;9,00%;89;2700,00;14;40;Premium;
CLI-007;PED-207;Exportadora Turolense SL;B67890123;11/06/2023;Aragón;44001;142.800,40 €;160;3600;-5,20%;6,00%;91;2600,45;15;30;Premium;Tasa negativa: probar clamp a 0%
CLI-008;PED-208;Almacenes Delta SA;A78901234;30/12/2023;Cataluña;08001;189.400,90 €;205;5100;105,30%;11,00%;112;3050,80;18;--;Premium;Score y tasa fuera de rango: probar clamp a 100
CLI-009;PED-209;Panadería Artesana SL;B89012345;05/02/2024;Aragón;50004;48.200,30 €;65;1800;42,10%;15,00%;70;1050,00;7;25;Estándar;
CLI-010;PED-210;Ferretería Central SA;A90123456;14/08/2023;Aragón;50005;52.900,00 €;58;1600;38,50%;18,00%;68;980,50;6;18;Estándar;
CLI-011;PED-211;Óptica Moderna SLU;B01234567;21/03/2024;Baleares;07001;39.700,80 €;72;2100;45,80%;12,50%;74;1150,25;8;12;Estándar;
CLI-012;PED-212;Papelería Escolar SL;B12345098;09/10/2022;Aragón;50006;44.500,20 €;60;1750;40,00%;20,00%;71;1020,00;7;n/a;Estándar;
CLI-013;PED-213;Talleres Mecánicos Ebro SA;A23456087;17/05/2023;Aragón;50007;56.300,00 €;80;2300;48,90%;14,00%;76;1250,60;9;8;Estándar;
CLI-014;PED-214;Cerrajería Rápida SLU;B34567076;02/12/2024;Aragón;50008;41.900,40 €;55;1500;36,20%;16,50%;65;950,00;6;s/n;Estándar;
CLI-015;PED-215;Floristería El Jardín SL;B45678065;25/06/2023;Aragón;50009;38.600,70 €;62;1650;39,50%;19,00%;69;890,30;5;15;Estándar;
CLI-016;PED-216;Librería Universitaria SA;A56789054;13/09/2024;Aragón;50010;49.100,50 €;68;1900;43,70%;13,00%;73;1080,90;8;nan;Estándar;
CLI-017;PED-217;Zapatería Confort SL;B67890043;07/01/2023;Aragón;50011;46.700,00 €;64;1780;41,30%;17,00%;72;1010,40;7;10;Estándar;
CLI-018;PED-218;Restaurante La Plaza SLU;B78901032;29/11/2024;Aragón;50012;53.800,90 €;78;2200;47,60%;9,50%;75;1200,00;9;null;Estándar;
CLI-019;PED-219;Kiosco Prensa SL;B89012021;18/04/2023;Aragón;50013;12.400,00 €;22;600;15,80%;25,00%;45;280,50;3;5;Básico;
CLI-020;PED-220;Mercería Doña Pilar SLU;B90123010;03/07/2024;País Vasco;01001;9.800,50 €;18;480;12,40%;30,00%;38;220,00;2;--;Básico;
CLI-021;PED-221;Frutería Ecológica SL;B01234109;26/02/2023;Aragón;50015;14.600,80 €;25;700;17,20%;22,00%;48;310,75;4;7;Básico;
CLI-022;PED-222;Copistería Rápida SA;A12345198;15/10/2024;Aragón;50016;8.900,00 €;16;450;10,50%;28,00%;35;190,20;2;n/d;Básico;
CLI-023;PED-223;Estanco Central SLU;B23456287;09/08/2023;Aragón;50017;11.200,40 €;20;550;14,00%;24,00%;42;260,00;3;undefined;Básico;
CLI-024;PED-224;Peluquería Estilo SL;B34567376;22/01/2024;Aragón;50019;13.700,60 €;23;620;16,50%;19,50%;46;295,50;3;4;Básico;
CLI-025;PED-225;Bazar Todo a Cien SA;A45678465;11/06/2023;Aragón;50020;7.500,00 €;14;400;9,20%;32,00%;33;175,00;2;1;Básico;
CLI-026;PED-226;Taller de Bicicletas SLU;B56789554;30/03/2024;Aragón;50021;10.300,20 €;19;510;13,10%;26,00%;40;240,80;3;nd;Básico;
CLI-027;PED-227;Tintorería Rápida SL;B67890643;05/12/2022;Aragón;50022;9.100,90 €;17;460;11,30%;29,00%;36;205,60;2;na;Básico;
CLI-028;PED-228;Pastelería Dulce Hogar SA;A78901732;19/09/2024;Aragón;50023;12.900,50 €;21;580;15,00%;21,00%;44;270,30;3;6;Básico;
CLI-029;PED-229;Corporación Global Iberia SA;A89012821;01/02/2025;Madrid;28001;850.000,00 €;480;42000;92,00%;3,00%;99;48500,00;35;500;Premium;Outlier extremo de gasto: probar IQR y Z-score
CLI-030;PED-230;Micro Emprendimiento SL;B90123910;14/07/2024;Aragón;50024;3.200,00 €;850;98000;2,10%;0,00%;12;95,00;1;0;Básico;Outlier extremo de visitas vs conversión: probar detección de anomalías
CLI-031;PED-231;Suministros Varios SL;B01234099;12/05/2023;Aragón;50025;n/d;45;1200;n/a;s/n;nan;null;5;undefined;Estándar;Fila con varios marcadores de ausencia distintos
CLI-032;PED-232;Comercial Aragonesa SA;A12345188;--;Aragón;50026;22.400,00 €;30;850;---;na;nd;450,00;4;--;Básico;Segunda fila con marcadores tipo guion"""


from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_dataset():
    """Carga y procesa el dataset de prueba en el storage mediante la API oficial."""
    file_bytes = io.BytesIO(SAMPLE_CSV_CONTENT.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("dataset_prueba_dataflow_ai_v1.6.csv", file_bytes, "text/csv")},
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]
    return DatasetService.get_dataset_metadata(dataset_id)


def test_fix1_observaciones_not_percentage_and_safety_net(sample_dataset):
    """FIX 1: Observaciones no debe clasificarse como percentage y convert_numeric debe abortar."""
    df = DatasetService.load_dataframe(sample_dataset.dataset_id)

    # 1. Semántica: Observaciones tiene texto con '%' en una celda, pero ratio_parseable es 0.0
    ratio, valid_cnt, total_real = get_numeric_parseable_ratio(df["Observaciones"])
    assert ratio < 0.8
    assert not is_percentage_or_score_column("Observaciones", df["Observaciones"])

    # 2. Profiler: el hint semántico no es PERCENTAGE
    profiling = ProfilerService.profile_dataset(sample_dataset.dataset_id)
    obs_prof = next(c for c in profiling.columns if c.column_name == "Observaciones")
    assert obs_prof.semantic_hint != SemanticHintEnum.PERCENTAGE
    assert obs_prof.inferred_type == ColumnTypeEnum.TEXT

    # 3. Reglas ETL: no se propone convert_numeric en Observaciones
    plan = ETLService.propose_plan_from_rules(sample_dataset.dataset_id)
    assert not any(s.column == "Observaciones" and s.operation == "convert_numeric" for s in plan.steps)

    # 4. Cinturón de seguridad: forzar convert_numeric en Observaciones levanta FunctionalException
    trans = ConvertNumericTransformation()
    with pytest.raises(FunctionalException) as exc_info:
        trans.apply(df, {"column": "Observaciones"})
    assert exc_info.value.code == "CONVERT_NUMERIC_DATA_LOSS"


def test_fix2_codigo_postal_preserves_leading_zeros(sample_dataset):
    """FIX 2: Codigo_Postal conserva ceros iniciales (08001, 07001, 01001) de punta a punta."""
    df = DatasetService.load_dataframe(sample_dataset.dataset_id)

    # 1. En el dataframe cargado
    cp_vals = df["Codigo_Postal"].tolist()
    assert "08001" in cp_vals
    assert "07001" in cp_vals
    assert "01001" in cp_vals

    # 2. En el profiling
    profiling = ProfilerService.profile_dataset(sample_dataset.dataset_id)
    cp_prof = next(c for c in profiling.columns if c.column_name == "Codigo_Postal")
    assert cp_prof.semantic_hint == SemanticHintEnum.ID
    assert cp_prof.inferred_type == ColumnTypeEnum.TEXT

    # 3. Tras ejecución del plan ETL y exportación limpia
    plan = ETLService.propose_plan_from_rules(sample_dataset.dataset_id)
    # Aprobar todos los pasos sugeridos
    for s in plan.steps:
        s.status = StepStatusEnum.APPROVED

    exec_result = ETLService.execute_plan(sample_dataset.dataset_id, plan.plan_id, plan.steps)
    assert exec_result.status == "completed"

    # Verificar que el CSV exportado conserva "08001"
    from app.core.storage import get_storage
    storage = get_storage()
    clean_csv_bytes = storage.read_file(f"{exec_result.run_id}_clean_{sample_dataset.filename}")
    clean_csv_str = clean_csv_bytes.decode("utf-8")
    assert "08001" in clean_csv_str
    assert "07001" in clean_csv_str
    assert "01001" in clean_csv_str


def test_fix3_clamp_range_percentage_floor_and_ceiling(sample_dataset):
    """FIX 3: clamp_range en columnas percentage fija siempre min_value=0.0 y max_value=100.0."""
    df = DatasetService.load_dataframe(sample_dataset.dataset_id)

    # 1. Motor de reglas propone min_value=0.0 y max_value=100.0 para Tasa_Conversion_Pct
    plan = ETLService.propose_plan_from_rules(sample_dataset.dataset_id)
    tasa_step = next(
        (s for s in plan.steps if s.column == "Tasa_Conversion_Pct" and s.operation == "clamp_range"),
        None,
    )
    assert tasa_step is not None
    assert tasa_step.parameters["min_value"] == 0.0
    assert tasa_step.parameters["max_value"] == 100.0

    # 2. Ejecutar clamp_range [0.0, 100.0] corrige tanto -5.20 como 105.30
    clamp = ClampRangeTransformation()
    # Pre-parsear a float para probar la transformación directa
    df_test = df.copy()
    df_test["Tasa_Conversion_Pct"] = to_numeric_series(df_test["Tasa_Conversion_Pct"])
    df_res, affected = clamp.apply(df_test, {"column": "Tasa_Conversion_Pct", "min_value": 0.0, "max_value": 100.0})

    # El valor negativo (-5.2) debe quedar en 0.0
    row_7_val = df_res.loc[6, "Tasa_Conversion_Pct"]
    assert row_7_val == 0.0

    # El valor superior (105.3) debe quedar en 100.0
    row_8_val = df_res.loc[7, "Tasa_Conversion_Pct"]
    assert row_8_val == 100.0


def test_fix4_null_count_unification(sample_dataset):
    """FIX 4: Profiling inicial reconoce exactamente los 14 nulos de Unidades_Stock."""
    profiling = ProfilerService.profile_dataset(sample_dataset.dataset_id)

    # Unidades_Stock tiene 14 marcadores de ausencia en el CSV:
    # CLI-003 (--), CLI-005 (n/d), CLI-008 (--), CLI-012 (n/a), CLI-014 (s/n),
    # CLI-016 (nan), CLI-018 (null), CLI-020 (--), CLI-022 (n/d), CLI-023 (undefined),
    # CLI-026 (nd), CLI-027 (na), CLI-031 (undefined), CLI-032 (--)
    stock_prof = next(c for c in profiling.columns if c.column_name == "Unidades_Stock")
    assert stock_prof.null_count == 14
    assert stock_prof.null_percentage == 43.75

    # Tasa_Conversion_Pct tiene 2 nulos (CLI-031 n/a, CLI-032 ---)
    tasa_prof = next(c for c in profiling.columns if c.column_name == "Tasa_Conversion_Pct")
    assert tasa_prof.null_count == 2
    assert tasa_prof.null_percentage == 6.25

    # Descuento_Pct tiene 2 nulos (CLI-031 s/n, CLI-032 na)
    desc_prof = next(c for c in profiling.columns if c.column_name == "Descuento_Pct")
    assert desc_prof.null_count == 2
    assert desc_prof.null_percentage == 6.25

    # Score_Calidad tiene 2 nulos (CLI-031 nan, CLI-032 nd)
    score_prof = next(c for c in profiling.columns if c.column_name == "Score_Calidad")
    assert score_prof.null_count == 2
    assert score_prof.null_percentage == 6.25

    # Al ejecutar convert_numeric en Unidades_Stock, los nulos resultantes son exactamente 14
    df = DatasetService.load_dataframe(sample_dataset.dataset_id)
    conv = ConvertNumericTransformation()
    df_clean, _ = conv.apply(df, {"column": "Unidades_Stock"})
    assert int(df_clean["Unidades_Stock"].isna().sum()) == 14


def test_fix5_spanish_decimal_gasto_medio_mensual(sample_dataset):
    """FIX 5: Gasto_Medio_Mensual con comas decimales se detecta y propone para convert_numeric."""
    profiling = ProfilerService.profile_dataset(sample_dataset.dataset_id)
    gasto_prof = next(c for c in profiling.columns if c.column_name == "Gasto_Medio_Mensual")

    # Inferencia de tipo numérica y hint moneda/cuantitativo
    assert gasto_prof.inferred_type == ColumnTypeEnum.NUMERIC
    assert gasto_prof.semantic_hint == SemanticHintEnum.CURRENCY

    # Quality Service detecta que necesita estandarización
    quality = QualityService.analyze_quality(sample_dataset.dataset_id)
    gasto_issue = next((i for i in quality.issues if i.column == "Gasto_Medio_Mensual"), None)
    assert gasto_issue is not None

    # Motor de reglas propone convert_numeric
    plan = ETLService.propose_plan_from_rules(sample_dataset.dataset_id)
    assert any(s.column == "Gasto_Medio_Mensual" and s.operation == "convert_numeric" for s in plan.steps)

    # Conversión exitosa a float puro
    df = DatasetService.load_dataframe(sample_dataset.dataset_id)
    conv = ConvertNumericTransformation()
    df_clean, _ = conv.apply(df, {"column": "Gasto_Medio_Mensual"})
    assert df_clean["Gasto_Medio_Mensual"].dtype == "float64"
    assert df_clean.loc[0, "Gasto_Medio_Mensual"] == 2450.75


@pytest.mark.anyio
async def test_ai_copilot_mock_plan_accuracy(sample_dataset):
    """Verifica que el Copiloto de IA Mock proponga un plan seguro y alineado con los 5 hallazgos."""
    ai_plan = await AIService.propose_ai_plan(sample_dataset.dataset_id, provider_name="mock")

    # 1. Observaciones nunca tiene convert_numeric
    assert not any(s.column == "Observaciones" and s.operation == "convert_numeric" for s in ai_plan.steps)

    # 2. Las columnas ID no tienen normalize_case
    for s in ai_plan.steps:
        if s.operation == "normalize_case":
            assert s.column not in ["ID_Cliente", "ID_Pedido", "Codigo_Postal", "CIF"]

    # 3. Gasto_Medio_Mensual tiene convert_numeric propuesto
    gasto_step = next((s for s in ai_plan.steps if s.column == "Gasto_Medio_Mensual" and s.operation == "convert_numeric"), None)
    assert gasto_step is not None

    # 4. Tasa_Conversion_Pct tiene clamp_range con [0.0, 100.0]
    tasa_step = next((s for s in ai_plan.steps if s.column == "Tasa_Conversion_Pct" and s.operation == "clamp_range"), None)
    assert tasa_step is not None
    assert tasa_step.parameters["min_value"] == 0.0
    assert tasa_step.parameters["max_value"] == 100.0
