"""
Tests del parseo numérico centralizado con separadores europeos y americanos.

Cubre el caso de negocio documentado en el README: importes como `1.200,50 €`
deben convertirse a 1200.50 (float64) y no perderse como NaN.
"""

import io
import math

import pandas as pd
from fastapi.testclient import TestClient

from app.core.number_parsing import parse_numeric_string
from app.main import app
from app.transformations.numeric_ops import ConvertNumericTransformation

client = TestClient(app)


def test_parse_numeric_string_european_and_american_formats():
    # Formato europeo (coma decimal, punto de millares)
    assert parse_numeric_string("1.200,50 €") == 1200.50
    assert parse_numeric_string("2.500,00") == 2500.00
    assert parse_numeric_string("1.234.567,89 €") == 1234567.89
    assert parse_numeric_string("350,75") == 350.75

    # Formato americano (punto decimal, coma de millares)
    assert parse_numeric_string("$1,234.56") == 1234.56
    assert parse_numeric_string("$350.00") == 350.00

    # Porcentajes, negativos y enteros
    assert parse_numeric_string("14.1%") == 14.1
    assert parse_numeric_string("-3") == -3.0
    assert parse_numeric_string("450") == 450.0

    # Marcadores de ausencia y texto no numérico
    assert parse_numeric_string("N/D") is None
    assert parse_numeric_string("N/A") is None
    assert parse_numeric_string("Laptop Pro 15") is None


def test_convert_numeric_transformation_preserves_european_values():
    df = pd.DataFrame({"Salario_EUR": ["1.200,50 €", "2.500,00 €", "N/D", "$1,234.56"]})
    transformation = ConvertNumericTransformation()
    result, _affected = transformation.apply(df.copy(), {"column": "Salario_EUR"})

    values = result["Salario_EUR"].tolist()
    assert values[0] == 1200.50
    assert values[1] == 2500.00
    assert math.isnan(values[2])  # N/D -> NaN explícito
    assert values[3] == 1234.56
    assert result["Salario_EUR"].dtype == "float64"


def test_european_numbers_end_to_end_pipeline():
    # CSV europeo real: delimitador ';' y decimales con coma
    csv_content = (
        "Fecha;Nombre_Empleado;Salario_EUR;Absentismo_Dias\n"
        "01/02/2026;Ana García;1.200,50 €;2\n"
        "02/02/2026;LUIS MARTINEZ;2.500,00 €;-3\n"
        "2026-02-03;Ana García;1.200,50 €;1\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("hr_european_test.csv", file_bytes, "text/csv")},
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    assert len(plan_data["steps"]) > 0

    approve_res = client.post(
        f"/api/v1/plans/{plan_data['plan_id']}/approve",
        json={"steps": plan_data["steps"]},
    )
    assert approve_res.status_code == 200
    run_data = approve_res.json()
    assert run_data["status"] == "completed"

    download_res = client.get(f"/api/v1/runs/{run_data['run_id']}/download")
    assert download_res.status_code == 200
    df_clean = pd.read_csv(io.StringIO(download_res.content.decode("utf-8")), sep=",")

    # Los salarios europeos se conservan con su valor real (no NaN ni valores corruptos)
    assert df_clean["Salario_EUR"].dtype == "float64"
    assert sorted(df_clean["Salario_EUR"].dropna().unique().tolist()) == [1200.5, 2500.0]

    # El absentismo negativo se acota a 0 y la fecha se estandariza a ISO
    assert (df_clean["Absentismo_Dias"] >= 0).all()
    assert "2026-02-01" in df_clean["Fecha"].astype(str).values
