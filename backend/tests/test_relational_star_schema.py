import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.relational_service import RelationalService

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
)

SYNTH_DETAILS = (
    "OrderDetailID,OrderID,ProductID,Quantity,UnitPrice,Discount\n"
    "DET001,ORD001,PROD01,5,15.50,0.05\n"
    "DET002,ORD001,PROD02,10,8.00,0.00\n"
    "DET003,ORD002,PROD01,2,15.50,0.10\n"
    "DET004,ORD003,PROD03,20,4.20,0.15\n"
)


def test_upload_batch_multiple_files():
    files = [
        ("files", ("customers.csv", io.BytesIO(SYNTH_CUSTOMERS.encode()), "text/csv")),
        ("files", ("products.csv", io.BytesIO(SYNTH_PRODUCTS.encode()), "text/csv")),
        ("files", ("orders.csv", io.BytesIO(SYNTH_ORDERS.encode()), "text/csv")),
        ("files", ("order_details.csv", io.BytesIO(SYNTH_DETAILS.encode()), "text/csv")),
    ]
    response = client.post("/api/v1/datasets/upload-batch", files=files)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 4
    filenames = [d["filename"] for d in data]
    assert "customers.csv" in filenames
    assert "order_details.csv" in filenames


def test_star_schema_inference_multi_table():
    # 1. Subir tablas
    files = [
        ("files", ("customers.csv", io.BytesIO(SYNTH_CUSTOMERS.encode()), "text/csv")),
        ("files", ("products.csv", io.BytesIO(SYNTH_PRODUCTS.encode()), "text/csv")),
        ("files", ("orders.csv", io.BytesIO(SYNTH_ORDERS.encode()), "text/csv")),
        ("files", ("order_details.csv", io.BytesIO(SYNTH_DETAILS.encode()), "text/csv")),
    ]
    up_res = client.post("/api/v1/datasets/upload-batch", files=files)
    assert up_res.status_code == 201
    dataset_ids = [d["dataset_id"] for d in up_res.json()]

    # 2. Inferir esquema de estrella
    schema_res = client.post("/api/v1/relational/star-schema", json={"dataset_ids": dataset_ids})
    assert schema_res.status_code == 200
    schema = schema_res.json()

    assert schema["fact_table"]["role"] == "fact"
    assert schema["fact_table"]["table_name"] == "order_details"
    assert len(schema["dimension_tables"]) >= 2
    dim_names = [d["table_name"] for d in schema["dimension_tables"]]
    assert "products" in dim_names
    assert "customers" in dim_names
    assert len(schema["relationships"]) >= 2

    # Verificar que las medidas DAX usan exactamente el nombre de tabla del modelo
    dax_measures = schema.get("suggested_dax_measures", {})
    assert "Total_Registros" in dax_measures
    assert dax_measures["Total_Registros"] == "COUNTROWS('order_details')"
    assert "Suma_Quantity" in dax_measures
    assert dax_measures["Suma_Quantity"] == "SUM('order_details'[Quantity])"
    assert "Ventas_Netas" in dax_measures or "Ventas_Totales" in dax_measures

    # Verificar que las relaciones son *:1 y tienen integridad referencial calculada
    for rel in schema["relationships"]:
        assert rel["cardinality"] == "*:1"
        assert rel["match_percentage"] == 100.0
        assert rel["is_referential_clean"] is True

    # 3. Comprobar TMDL export
    model_id = schema["model_id"]
    tmdl_res = client.get(f"/api/v1/relational/models/{model_id}/tmdl")
    assert tmdl_res.status_code == 200
    assert "model Model" in tmdl_res.text
    assert "ref table 'order_details'" in tmdl_res.text
    assert "relationship" in tmdl_res.text
