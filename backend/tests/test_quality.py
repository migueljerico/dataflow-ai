import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_quality_analysis_contact_center():
    csv_content = (
        "Fecha,Campana,ID_Agente,Nombre_Agente,Llamadas_Atendidas,Ventas_Conseguidas,Conversion_Pct,AHT_Segundos,Score_Calidad,Absentismo\n"
        "2026-02-01, Retencion ,AGT-101, Laura Fernandez ,85,12,14.1%,420,95.5%,No\n"
        "2026-02-01, Retencion ,AGT-101, Laura Fernandez ,85,12,14.1%,420,95.5%,No\n"
        "02/02/2026,retencion,AGT-103,Sofia Loren,70,15,21.4%, 510 ,72.0 %,Si\n"
        "2026-02-04,Soporte Tecnico,AGT-105, Lucia Blanco ,95,5,5.2%, 600 ,105.0%,NO\n"
        "2026-02-05,Soporte Tecnico,AGT-106,Ramon Sampedro,100,2,2.0%,-50,82.5%,No\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))

    upload_res = client.post("/api/v1/datasets/upload", files={"file": ("cc_quality_test.csv", file_bytes, "text/csv")})
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    q_res = client.get(f"/api/v1/datasets/{dataset_id}/quality")
    assert q_res.status_code == 200
    q_data = q_res.json()

    assert "quality_score" in q_data
    score = q_data["quality_score"]
    assert 0.0 <= score["overall_score"] <= 100.0
    assert "completeness" in score
    assert "validity" in score
    assert "consistency" in score
    assert "uniqueness" in score
    assert "integrity" in score

    # Verificar que detectó problemas accionables
    issues = q_data["issues"]
    assert len(issues) > 0

    dimensions = [i["dimension"] for i in issues]
    assert "uniqueness" in dimensions  # Fila 1 y 2 duplicadas
    assert "consistency" in dimensions  # ' Retencion ' con espacios o 'retencion' minuscula
    assert "integrity" in dimensions  # -50 segundos AHT o 105.0% Score_Calidad
