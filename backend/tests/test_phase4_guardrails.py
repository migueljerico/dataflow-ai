import pytest
import io
import pandas as pd
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.services.dataset_service import DatasetService
from app.services.profiler_service import ProfilerService
from app.models.profiling import ColumnTypeEnum, SemanticHintEnum


def test_detect_csv_encoding_utf8():
    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        f.write("id,nombre,valor\n1,España,100\n".encode("utf-8"))
        f_path = Path(f.name)
    try:
        enc = DatasetService._detect_csv_encoding(f_path)
        assert enc.lower() in ("utf-8", "ascii")
    finally:
        f_path.unlink(missing_ok=True)


def test_detect_csv_encoding_utf8_bom():
    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        # Escribir con marca de orden de bytes (BOM) UTF-8
        f.write("\ufeffid,nombre,ciudad\n1,Marta,Valencia\n".encode("utf-8-sig"))
        f_path = Path(f.name)
    try:
        enc = DatasetService._detect_csv_encoding(f_path)
        assert "utf-8" in enc.lower()
    finally:
        f_path.unlink(missing_ok=True)


def test_detect_csv_encoding_windows1252():
    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        # Texto en Windows-1252 con tildes y eñes
        content = "código;descripción;país;año\n101;Operación rápida;España;2026\n"
        f.write(content.encode("windows-1252"))
        f_path = Path(f.name)
    try:
        enc = DatasetService._detect_csv_encoding(f_path)
        assert enc.lower() in ("windows-1252", "iso-8859-1", "latin-1")
    finally:
        f_path.unlink(missing_ok=True)


def test_process_saved_dataset_strips_bom_and_normalizes_windows1252():
    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        content = "código;dirección;año\n08001;Calle Mayor, 12;2026\n"
        f.write(content.encode("windows-1252"))
        f_path = Path(f.name)
    try:
        meta = DatasetService._process_saved_dataset_file(
            saved_path=f_path,
            filename="windows_data.csv",
            file_ext=".csv",
            file_size=f_path.stat().st_size,
            dataset_id="test-win1252",
        )
        assert "código" in meta.columns
        assert "dirección" in meta.columns
        assert "año" in meta.columns
        assert meta.row_count == 1
        assert meta.column_count == 3
    finally:
        f_path.unlink(missing_ok=True)


def test_semantic_hint_id_priority_over_currency_and_date():
    # 1. id_precio_tarifa no debe clasificarse como CURRENCY
    series_precio_id = pd.Series(["T-01", "T-02", "T-03"])
    hint_precio = ProfilerService._detect_semantic_hint("id_precio_tarifa", series_precio_id, ColumnTypeEnum.TEXT)
    assert hint_precio == SemanticHintEnum.ID

    # 2. id_alta_empleado no debe clasificarse como DATE
    series_alta_id = pd.Series(["ALT-001", "ALT-002", "ALT-003"])
    hint_alta = ProfilerService._detect_semantic_hint("id_alta_empleado", series_alta_id, ColumnTypeEnum.TEXT)
    assert hint_alta == SemanticHintEnum.ID

    # 3. codigo_postal con ceros a la izquierda debe ser ID y TEXT
    series_cp = pd.Series(["08001", "28079", "01004", "03001"])
    hint_cp = ProfilerService._detect_semantic_hint("codigo_postal", series_cp, ColumnTypeEnum.TEXT)
    type_cp = ProfilerService._infer_column_type(series_cp, col_name="codigo_postal")
    assert hint_cp == SemanticHintEnum.ID
    assert type_cp == ColumnTypeEnum.TEXT

    # 4. cod_municipio_ine debe ser ID y TEXT
    series_ine = pd.Series(["08019", "28079", "41091"])
    hint_ine = ProfilerService._detect_semantic_hint("cod_municipio_ine", series_ine, ColumnTypeEnum.TEXT)
    type_ine = ProfilerService._infer_column_type(series_ine, col_name="cod_municipio_ine")
    assert hint_ine == SemanticHintEnum.ID
    assert type_ine == ColumnTypeEnum.TEXT


def test_semantic_hint_currency_and_date_clean_columns():
    # Precio real debe ser CURRENCY
    series_money = pd.Series(["12.50 €", "19.99 €", "5.00 €"])
    hint_money = ProfilerService._detect_semantic_hint("importe_total", series_money, ColumnTypeEnum.NUMERIC)
    assert hint_money == SemanticHintEnum.CURRENCY

    # Fecha real debe ser DATE
    series_date = pd.Series(["2026-01-15", "2026-02-20", "2026-03-25"])
    hint_date = ProfilerService._detect_semantic_hint("fecha_factura", series_date, ColumnTypeEnum.DATETIME)
    assert hint_date == SemanticHintEnum.DATE
