import io
import pandas as pd
import pytest
from app.main import app
from app.models.etl import StepStatusEnum
from fastapi.testclient import TestClient

client = TestClient(app)


def test_parquet_export_end_to_end_contact_center():
    """
    Verifica que la ejecución de un plan ETL genere y almacene automáticamente
    el dataset limpio serializado en Apache Parquet, y que los endpoints REST
    permitan su descarga íntegra y deserialización correcta en pandas.
    """
    # 1. Cargar dataset demo
    res_load = client.post("/api/v1/datasets/samples/contact_center/load")
    assert res_load.status_code == 201
    dataset = res_load.json()
    dataset_id = dataset["dataset_id"]

    # 2. Proponer plan de reglas
    res_plan = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert res_plan.status_code == 201
    plan = res_plan.json()
    plan_id = plan["plan_id"]

    # 3. Aprobar todos los pasos
    steps = plan["steps"]
    for s in steps:
        s["status"] = StepStatusEnum.APPROVED.value

    # 4. Ejecutar plan
    res_exec = client.post(f"/api/v1/plans/{plan_id}/approve", json={"steps": steps})
    assert res_exec.status_code == 200
    result = res_exec.json()
    run_id = result["run_id"]

    # Verificar metadatos de Parquet en ExecutionResult
    assert result["parquet_filename"] is not None
    assert result["parquet_filename"].endswith(".parquet")
    assert result["parquet_url"] == f"/api/v1/runs/{run_id}/download-parquet"

    # 5. Descargar vía endpoint primario /download-parquet
    res_download = client.get(f"/api/v1/runs/{run_id}/download-parquet")
    assert res_download.status_code == 200
    assert res_download.headers["content-type"] == "application/vnd.apache.parquet"

    # Validar Magic Number de Apache Arrow / Parquet (PAR1)
    parquet_bytes = res_download.content
    assert len(parquet_bytes) > 100
    assert parquet_bytes[:4] == b"PAR1"
    assert parquet_bytes[-4:] == b"PAR1"

    # 6. Deserializar con pandas read_parquet y validar integridad dimensional
    df_parquet = pd.read_parquet(io.BytesIO(parquet_bytes))
    assert len(df_parquet) == result["rows_after"]
    assert len(df_parquet.columns) == result["columns_after"]

    # 7. Descargar vía alias /download/parquet y /parquet
    res_alias1 = client.get(f"/api/v1/runs/{run_id}/download/parquet")
    assert res_alias1.status_code == 200
    assert res_alias1.content[:4] == b"PAR1"

    res_alias2 = client.get(f"/api/v1/runs/{run_id}/parquet")
    assert res_alias2.status_code == 200
    assert res_alias2.content[:4] == b"PAR1"


def test_parquet_download_not_found():
    """
    Verifica que la solicitud de descarga Parquet para una ejecución inexistente
    retorne HTTP 404 con código de error descriptivo.
    """
    res = client.get("/api/v1/runs/RUN-nonexistent/download-parquet")
    assert res.status_code == 404
    data = res.json()
    assert data["error"] is True
