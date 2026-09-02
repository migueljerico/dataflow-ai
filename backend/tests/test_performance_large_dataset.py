import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.models.etl import ExecutionResult
from app.services.analytics_service import AnalyticsService
from app.services.profiler_service import ProfilerService
from app.services.quality_service import QualityService
from app.transformations.numeric_ops import ClampRangeTransformation, ConvertNumericTransformation
from app.transformations.text_ops import TrimTextTransformation


@pytest.fixture
def large_dataset_100k() -> pd.DataFrame:
    """Genera un dataset sintético representativo de negocio de 100.000 filas."""
    n_rows = 100_000

    # 1. IDs con ceros a la izquierda
    tx_ids = [f"TX-{i:06d}" for i in range(n_rows)]

    # 2. Códigos postales españoles preservando ceros
    cp_list = ["08001", "07001", "28001", "41001", "01001"] * (n_rows // 5)

    # 3. Importes con separadores regionales europeos y marcadores
    importes = ["1.250,50", "99,95", "--", "450,00", "2.100,75"] * (n_rows // 5)

    # 4. Porcentajes que requieren clamping [0.0, 100.0]
    margenes = [-5.0, 25.5, 115.0, 50.0, 80.0] * (n_rows // 5)

    # 5. Fechas heterogéneas
    fechas = ["2026-01-15", "15/02/2026", "2026-03-01", "01/04/2026", "2026-05-10"] * (n_rows // 5)

    # 6. Categorías comerciales
    canales = ["Online", "Retail", "Distribución", "Directo", "Telefónica"] * (n_rows // 5)

    # 7. Unidades cuantitativas enteras
    unidades = [10, 5, 20, 100, 1] * (n_rows // 5)

    # 8. Texto libre con espacios
    notas = [
        "  Pedido estándar con entrega urgente  ",
        "Cliente SA",
        "Nota interna",
        " Sin incidencias ",
        "Revisado",
    ] * (n_rows // 5)

    df = pd.DataFrame(
        {
            "ID_Transaccion": tx_ids,
            "Codigo_Postal": cp_list,
            "Fecha_Operacion": fechas,
            "Importe_Euros": importes,
            "Margen_Pct": margenes,
            "Canal_Venta": canales,
            "Unidades_Stock": unidades,
            "Observaciones": notas,
        }
    )
    return df


def test_profiler_performance_100k_rows(large_dataset_100k: pd.DataFrame):
    """Verifica que el perfilado de 100.000 filas se complete rápidamente y con tipos correctos."""
    t0 = time.perf_counter()
    report = ProfilerService.profile_dataframe(large_dataset_100k)
    duration = time.perf_counter() - t0

    assert report.row_count == 100_000
    assert report.column_count == 8
    # Comprobar que IDs y códigos postales preservan rol de ID / text
    cp_col = next((c for c in report.columns if c.column_name == "Codigo_Postal"), None)
    assert cp_col is not None
    assert cp_col.semantic_hint == "id"

    # Tiempo de ejecución: debe ser < 30.0 segundos para 100.000 filas
    assert duration < 30.0, f"Profiling de 100k filas tardó {duration:.2f}s (umbral: 30.0s)"


def test_quality_analysis_performance_100k_rows(large_dataset_100k: pd.DataFrame):
    """Verifica que el motor de calidad analice 100.000 filas en tiempo reducido."""
    profile = ProfilerService.profile_dataframe(large_dataset_100k)

    t0 = time.perf_counter()
    quality = QualityService.analyze_dataframe(large_dataset_100k, profile)
    duration = time.perf_counter() - t0

    assert quality.quality_score.overall_score >= 0
    assert len(quality.issues) > 0
    # Tiempo de ejecución de calidad: debe ser < 25.0 segundos para 100.000 filas
    assert duration < 25.0, f"Quality check de 100k filas tardó {duration:.2f}s (umbral: 25.0s)"


def test_transformations_performance_100k_rows(large_dataset_100k: pd.DataFrame):
    """Verifica que las transformaciones vectorizadas procesen 100.000 filas a alta velocidad."""
    df = large_dataset_100k.copy()

    # 1. ConvertNumericTransformation sobre 100.000 celdas europeas
    t0 = time.perf_counter()
    conv_trans = ConvertNumericTransformation()
    df_conv, _ = conv_trans.apply(df, {"column": "Importe_Euros"})
    t_conv = time.perf_counter() - t0
    assert t_conv < 3.8, f"ConvertNumeric tardó {t_conv:.2f}s (umbral: 3.8s)"
    assert pd.api.types.is_float_dtype(df_conv["Importe_Euros"])
    assert df_conv["Importe_Euros"].iloc[0] == 1250.50
    assert pd.isna(df_conv["Importe_Euros"].iloc[2])  # Marcador '--' convertido a NaN

    # 2. ClampRangeTransformation sobre 100.000 valores porcentuales
    t0 = time.perf_counter()
    clamp_trans = ClampRangeTransformation()
    df_clamp, _ = clamp_trans.apply(df, {"column": "Margen_Pct", "min_value": 0.0, "max_value": 100.0})
    t_clamp = time.perf_counter() - t0
    assert t_clamp < 1.0, f"ClampRange tardó {t_clamp:.2f}s (umbral: 1.0s)"
    assert df_clamp["Margen_Pct"].min() >= 0.0
    assert df_clamp["Margen_Pct"].max() <= 100.0

    # 3. TrimTextTransformation sobre 100.000 strings
    t0 = time.perf_counter()
    trim_trans = TrimTextTransformation()
    df_trim, _ = trim_trans.apply(df, {"column": "Observaciones"})
    t_trim = time.perf_counter() - t0
    assert t_trim < 1.5, f"TrimText tardó {t_trim:.2f}s (umbral: 1.5s)"
    assert df_trim["Observaciones"].iloc[0] == "Pedido estándar con entrega urgente"


def test_parquet_serialization_performance_100k_rows(tmp_path: Path, large_dataset_100k: pd.DataFrame):
    """Verifica que la serialización Parquet de 100.000 filas sea rápida y reduzca tamaño vs CSV."""
    csv_path = tmp_path / "dataset_100k.csv"
    parquet_path = tmp_path / "dataset_100k.parquet"

    # CSV
    t0 = time.perf_counter()
    large_dataset_100k.to_csv(csv_path, index=False)
    t_csv = time.perf_counter() - t0

    # Parquet
    t0 = time.perf_counter()
    large_dataset_100k.to_parquet(parquet_path, index=False, engine="pyarrow", compression="snappy")
    t_parquet = time.perf_counter() - t0

    assert t_parquet < 2.5, f"Parquet write tardó {t_parquet:.2f}s (umbral: 2.5s)"

    # Comprobar reducción de tamaño (Parquet debe ser sensiblemente menor que CSV)
    csv_size = csv_path.stat().st_size
    parquet_size = parquet_path.stat().st_size
    assert parquet_size < csv_size, f"Parquet ({parquet_size} B) debe ser menor que CSV ({csv_size} B)"

    # Leer de vuelta y verificar integridad de tipos y ceros
    df_read = pd.read_parquet(parquet_path)
    assert len(df_read) == 100_000
    assert df_read["Codigo_Postal"].iloc[0] == "08001"
    assert df_read["Codigo_Postal"].iloc[1] == "07001"


def test_integration_guide_generation_100k_rows(large_dataset_100k: pd.DataFrame):
    """Verifica que la Guía de Integración para Power BI y Excel se adapte fielmente al dataset de 100k."""
    # Simular dataframe limpio con tipos aplicados
    clean_df = large_dataset_100k.copy()
    clean_df["Importe_Euros"] = [1250.50, 99.95, np.nan, 450.00, 2100.75] * (100_000 // 5)
    clean_df["Margen_Pct"] = [0.0, 25.5, 100.0, 50.0, 80.0] * (100_000 // 5)

    mock_run_result = ExecutionResult(
        run_id="run-perf-100k",
        dataset_id="ds-perf-100k",
        plan_id="plan-perf-100k",
        status="completed",
        started_at=pd.Timestamp.now(),
        finished_at=pd.Timestamp.now(),
        rows_before=100_000,
        rows_after=100_000,
        columns_before=8,
        columns_after=8,
        applied_steps_count=4,
        input_hash_md5="hash_in",
        output_hash_md5="hash_out",
        clean_filename="ventas_retail_clean.csv",
        download_url="/download/csv",
        script_url="/download/script",
        parquet_filename="ventas_retail_clean.parquet",
        parquet_url="/download/parquet",
    )

    guide = AnalyticsService._build_integration_guide(clean_df, mock_run_result, domain="sales")

    assert guide.table_name == "Ventas_Retail_Clean"
    assert guide.clean_filename == "ventas_retail_clean.csv"
    assert guide.parquet_filename == "ventas_retail_clean.parquet"
    assert guide.row_count == 100_000

    # 1. Power Query M debe contener tipos específicos
    assert 'File.Contents("ventas_retail_clean.csv")' in guide.power_query_m_csv
    assert '{"ID_Transaccion", type text}' in guide.power_query_m_csv
    assert '{"Codigo_Postal", type text}' in guide.power_query_m_csv
    assert '{"Importe_Euros", type number}' in guide.power_query_m_csv
    assert '{"Unidades_Stock", Int64.Type}' in guide.power_query_m_csv
    assert '{"Fecha_Operacion", type date}' in guide.power_query_m_csv

    # 2. Power Query M Parquet
    assert guide.power_query_m_parquet is not None
    assert 'Parquet.Document(File.Contents("ventas_retail_clean.parquet"))' in guide.power_query_m_parquet

    # 3. Medidas DAX Contextuales
    dax_names = [m.name for m in guide.dax_measures]
    assert "Total_Registros" in dax_names
    assert "Total_Importe_Euros" in dax_names
    assert "Promedio_Importe_Euros" in dax_names
    assert "Total_Unidades_Stock" in dax_names
    assert any("COUNTROWS('Ventas_Retail_Clean')" in m.formula for m in guide.dax_measures)
    assert any("SUM('Ventas_Retail_Clean'[Importe_Euros])" in m.formula for m in guide.dax_measures)

    # 4. Fórmulas Excel Adaptativas
    assert len(guide.excel_formulas) > 0
    first_excel = guide.excel_formulas[0]
    # Comprobar que referencia el rango real de 100.000 filas ($D$2:$D$100001)
    assert "$100001" in first_excel.formula_es
    assert "SI(ESNUMERO(" in first_excel.formula_es
    assert "IF(ISNUMBER(" in first_excel.formula_en
