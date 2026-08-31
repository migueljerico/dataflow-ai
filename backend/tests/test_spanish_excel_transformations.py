import io
import pandas as pd
from app.core.number_parsing import parse_numeric_string, to_numeric_series
from app.transformations.numeric_ops import ConvertNumericTransformation, ClampRangeTransformation
from app.transformations.datetime_ops import ConvertDatetimeTransformation
from app.transformations.text_ops import NormalizeCaseTransformation


def test_spanish_decimal_comma_and_thousands_period():
    assert parse_numeric_string("1.234,56") == 1234.56
    assert parse_numeric_string("1.234.567,89") == 1234567.89
    assert parse_numeric_string("12,5%") == 12.5
    assert parse_numeric_string("0,75") == 0.75
    assert parse_numeric_string("N/D") is None
    assert parse_numeric_string("--") is None


def test_spanish_date_conversions():
    transformer = ConvertDatetimeTransformation()
    df = pd.DataFrame({"Fecha_Factura": ["01/02/2026", "15/08/2025", "2026-03-31", "invalid_date"]})
    df_clean, affected = transformer.apply(df, {"column": "Fecha_Factura", "target_format": "%Y-%m-%d"})

    assert df_clean["Fecha_Factura"].iloc[0] == "2026-02-01"
    assert df_clean["Fecha_Factura"].iloc[1] == "2025-08-15"
    assert df_clean["Fecha_Factura"].iloc[2] == "2026-03-31"
    assert pd.isna(df_clean["Fecha_Factura"].iloc[3])
    assert affected >= 2


def test_spanish_business_acronyms_preservation():
    transformer = NormalizeCaseTransformation()
    df = pd.DataFrame({"Empresa": ["CONSTRUCCIONES LOPEZ SL", "TALLERES PEREZ SA", "CLIENTE CIF B12345678"]})
    df_clean, affected = transformer.apply(df, {"column": "Empresa", "mode": "title"})

    assert "SL" in df_clean["Empresa"].iloc[0]
    assert "SA" in df_clean["Empresa"].iloc[1]
    assert "CIF" in df_clean["Empresa"].iloc[2]


def test_convert_numeric_transformation_spanish_excel_series():
    transformer = ConvertNumericTransformation()
    df = pd.DataFrame({"Importe_EUR": ["1.200,50 €", "350,00 €", "-50,00 €", "N/A"]})
    df_clean, affected = transformer.apply(df, {"column": "Importe_EUR"})

    assert df_clean["Importe_EUR"].iloc[0] == 1200.50
    assert df_clean["Importe_EUR"].iloc[1] == 350.00
    assert df_clean["Importe_EUR"].iloc[2] == -50.00
    assert pd.isna(df_clean["Importe_EUR"].iloc[3])
