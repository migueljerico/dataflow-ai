import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_etl_pipeline_flow():
    csv_content = (
        "Fecha,ID_Cliente,Nombre_Cliente,Producto,Cantidad,Precio_Unidad,Canal,Comercial\n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "06/01/2026,CLI-002,María Gómez,Monitor 4K,1,$350.00,Tienda,Ana Belén\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/datasets/upload", files={"file": ("sales_pipeline_test.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]
    assert len(plan_data["steps"]) > 0

    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": plan_data["steps"]})
    assert approve_res.status_code == 200
    run_data = approve_res.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "completed"
    assert run_data["rows_before"] == 3
    assert run_data["rows_after"] == 2  # Se eliminó el duplicado

    download_res = client.get(f"/api/v1/runs/{run_id}/download")
    assert download_res.status_code == 200
    assert len(download_res.content) > 0

    script_res = client.get(f"/api/v1/runs/{run_id}/script")
    assert script_res.status_code == 200
    script_text = script_res.text
    assert "import pandas as pd" in script_text
    assert "def run_etl_pipeline" in script_text


def test_clamp_range_logging_accuracy():
    csv_content = "Nombre_Agente,AHT_Segundos,Score_Calidad\n" "Ramon Sampedro,-50,85.0\n" "Lucia Blanco,450,105.0\n"
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/datasets/upload", files={"file": ("contact_center_clamp_test.csv", file_bytes, "text/csv")}
    )
    dataset_id = upload_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]

    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": plan_data["steps"]})
    run_data = approve_res.json()
    audit_logs = run_data["audit_logs"]

    aht_log = [l for l in audit_logs if "AHT_Segundos" in l and "clamp_range" in l]
    assert len(aht_log) > 0
    assert "[0, inf]" in aht_log[0]
    assert "[0, 100.0]" not in aht_log[0]

    score_log = [l for l in audit_logs if "Score_Calidad" in l and "clamp_range" in l]
    assert len(score_log) > 0
    assert "100.0" in score_log[0]


def test_sales_sample_end_to_end_qa():
    csv_content = (
        "Fecha,ID_Cliente,Nombre_Cliente,Producto,Cantidad,Precio_Unidad,Canal,Comercial\n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
        "06/01/2026,CLI-002,María Gómez,Monitor 4K,1,$350.00,Tienda,Ana Belén\n"
        "07-01-2026,CLI-003, LUIS MARTINEZ ,Teclado Mecánico,N/A,85.00 €,WEB,Carlos Ruiz\n"
        "2026/01/08,CLI-004,Ana Belén,Ratón Ergonómico,-1,45.00 €,TIENDA,Ana Belén\n"
        "invalid_date,CLI-005,Elena Nito,Soporte Monitor,1,25.00 €,Web,Carlos Ruiz\n"
        "2026-01-10,CLI-006,SOPORTE SA,Pack Cables,5,15.50 €,Tienda,Ana Belén\n"
        ",,,,,,,\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/datasets/upload", files={"file": ("sales_sample_corrupted_qa.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]

    approve_res = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": plan_data["steps"]})
    assert approve_res.status_code == 200
    run_data = approve_res.json()

    # 1. Conteo de filas resultante (1 duplicado eliminado, 1 fila vacía purgada)
    assert run_data["rows_after"] == 6

    audit_logs = run_data["audit_logs"]

    # 2. Log de fila vacía
    empty_log = [l for l in audit_logs if "drop_empty_rows" in l]
    assert len(empty_log) > 0
    assert "1 fila(s) completamente vacías" in empty_log[0]

    # 3. Log de fecha inválida
    date_log = [l for l in audit_logs if "convert_datetime" in l]
    assert len(date_log) > 0
    assert "formato inválido irrecuperable" in date_log[0]

    # 4. Descargar y parsear con pandas para validación rigurosa
    download_res = client.get(f"/api/v1/runs/{run_data['run_id']}/download")
    clean_csv_text = download_res.content.decode("utf-8")
    df_clean = pd.read_csv(io.StringIO(clean_csv_text))

    assert "Soporte SA" in df_clean["Nombre_Cliente"].values or "SOPORTE SA" in df_clean["Nombre_Cliente"].values
    assert "Luis Martinez" in df_clean["Nombre_Cliente"].values
    assert (df_clean["Cantidad"].dropna() < 0).sum() == 0  # 0 cantidades negativas
    assert df_clean["Precio_Unidad"].dtype == "float64"  # Columna tipada a float64
