import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_profiling_sales_corrupted():
    csv_content = (
        "Fecha,ID_Cliente,Nombre_Cliente,Producto,Cantidad,Precio_Unidad,Canal,Comercial\n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "06/01/2026,CLI-002,María Gómez,Monitor 4K,1,$350.00,Tienda,Ana Belén\n"
        ",CLI-003,Pedro Picapiedra,Teclado Mecanico,3,45.00,WEB,Carlos Ruiz\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sales_test.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    prof_res = client.get(f"/api/v1/datasets/{dataset_id}/profiling")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()

    assert prof_data["dataset_id"] == dataset_id
    assert prof_data["row_count"] == 4
    assert prof_data["column_count"] == 8
    assert prof_data["duplicates_count"] == 1  # Fila 1 y 2 son duplicadas exactas
    assert len(prof_data["columns"]) == 8

    # Verificar sugerencias semánticas
    col_map = {c["column_name"]: c for c in prof_data["columns"]}
    assert col_map["Fecha"]["semantic_hint"] in ["date", "datetime"]
    assert col_map["ID_Cliente"]["semantic_hint"] == "id"
    assert col_map["Precio_Unidad"]["semantic_hint"] == "currency"
    assert col_map["Nombre_Cliente"]["semantic_hint"] == "name"
