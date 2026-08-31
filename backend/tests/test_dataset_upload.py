import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DataFlow AI"
    assert data["status"] == "online"


def test_upload_valid_csv():
    csv_content = "ID,Nombre,Importe\n1, Juan ,100.5\n2,María,200.0\n"
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post("/api/v1/datasets/upload", files={"file": ("test_sales.csv", file_bytes, "text/csv")})

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_sales.csv"
    assert data["file_type"] == "csv"
    assert data["row_count"] == 2
    assert data["column_count"] == 3
    assert data["columns"] == ["ID", "Nombre", "Importe"]
    assert data["status"] == "validated"
    assert "dataset_id" in data

    # Probar endpoint GET por dataset_id
    dataset_id = data["dataset_id"]
    get_response = client.get(f"/api/v1/datasets/{dataset_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["dataset_id"] == dataset_id


def test_upload_valid_xlsx():
    df = pd.DataFrame(
        {"Empleado": ["Carlos", "Ana"], "Departamento": ["Operaciones", "RRHH"], "Sueldo": [30000, 32000]}
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Empleados")
    buffer.seek(0)

    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("hr_data.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "hr_data.xlsx"
    assert data["file_type"] == "xlsx"
    assert data["row_count"] == 2
    assert data["column_count"] == 3
    assert data["columns"] == ["Empleado", "Departamento", "Sueldo"]


def test_upload_invalid_extension():
    file_bytes = io.BytesIO(b"Some text content")
    response = client.post("/api/v1/datasets/upload", files={"file": ("document.pdf", file_bytes, "application/pdf")})

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "INVALID_FILE_TYPE"
    assert "Formato no soportado" in data["message"]


def test_upload_empty_file():
    file_bytes = io.BytesIO(b"")
    response = client.post("/api/v1/datasets/upload", files={"file": ("empty.csv", file_bytes, "text/csv")})

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "EMPTY_FILE"
    assert "vacío" in data["message"]


def test_upload_file_too_large():
    # Crear un contenido que simule superar el límite configurado
    original_limit = settings.MAX_FILE_SIZE_BYTES
    settings.MAX_FILE_SIZE_BYTES = 100  # Límite temporal de 100 bytes para test

    try:
        large_content = "ID,Nombre\n" + ("1,TestValueLargeRow\n" * 10)
        file_bytes = io.BytesIO(large_content.encode("utf-8"))
        response = client.post("/api/v1/datasets/upload", files={"file": ("large_file.csv", file_bytes, "text/csv")})

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["code"] == "FILE_TOO_LARGE"
        assert "supera el límite" in data["message"]
    finally:
        settings.MAX_FILE_SIZE_BYTES = original_limit


def test_get_nonexistent_dataset():
    response = client.get("/api/v1/datasets/non_existent_uuid_123")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "DATASET_NOT_FOUND"
