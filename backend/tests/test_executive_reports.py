"""
Reportes ejecutivos PDF/HTML, exportación programada y webhooks de drift (v1.16.0).

Cobertura:
- Exportación directa PDF (magic bytes %PDF) y HTML por run.
- CRUD de programaciones + ejecución forzada (run-now) + descarga del último reporte.
- run_due_schedules: solo ejecuta las programaciones vencidas.
- Gobernanza del webhook: validación SSRF en el alta (IP privada y esquema no HTTP),
  trigger 'always' entrega siempre y 'critical_drift' solo con drift crítico.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.report import WebhookDeliveryResult
from app.services.report_service import REPORT_SCHEDULES, ReportService

client = TestClient(app)

# IP pública literal (evita resolución DNS en tests) para el alta de webhooks
PUBLIC_WEBHOOK_URL = "http://93.184.216.34/webhook"


def _completed_run_id() -> str:
    load_res = client.post("/api/v1/datasets/samples/sales/load")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]
    plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
    assert plan_res.status_code == 201
    plan = plan_res.json()
    appr = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": plan["steps"]})
    assert appr.status_code == 200
    return appr.json()["run_id"]


class TestDirectExport:
    def test_pdf_export(self):
        run_id = _completed_run_id()
        res = client.get(f"/api/v1/reports/{run_id}/pdf?lang=es")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF")
        assert len(res.content) > 1500
        assert f"reporte_ejecutivo_{run_id}.pdf" in res.headers["content-disposition"]

    def test_pdf_export_english(self):
        run_id = _completed_run_id()
        res = client.get(f"/api/v1/reports/{run_id}/pdf?lang=en")
        assert res.status_code == 200 and res.content.startswith(b"%PDF")

    def test_pdf_export_idioma_desconocido_caer_en_es(self):
        run_id = _completed_run_id()
        res = client.get(f"/api/v1/reports/{run_id}/pdf?lang=xx")
        assert res.status_code == 200 and res.content.startswith(b"%PDF")

    def test_html_export(self):
        run_id = _completed_run_id()
        res = client.get(f"/api/v1/reports/{run_id}/html")
        assert res.status_code == 200
        assert "<html" in res.text.lower()

    def test_export_run_inexistente_404(self):
        res = client.get("/api/v1/reports/RUN-NOEXISTE/pdf")
        assert res.status_code == 404
        assert res.json()["code"] == "RUN_NOT_FOUND"


class TestScheduleCrud:
    def test_ciclo_completo_programacion_pdf(self):
        run_id = _completed_run_id()
        create = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "report_format": "pdf", "interval_minutes": 30},
        )
        assert create.status_code == 201
        sched = create.json()
        schedule_id = sched["schedule_id"]
        assert schedule_id.startswith("SCHED-")
        assert sched["executions_count"] == 0
        assert sched["next_run_at"] is not None

        listing = client.get("/api/v1/reports/schedules")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        detail = client.get(f"/api/v1/reports/schedules/{schedule_id}")
        assert detail.status_code == 200 and detail.json()["run_id"] == run_id

        run_now = client.post(f"/api/v1/reports/schedules/{schedule_id}/run-now")
        assert run_now.status_code == 200
        log = run_now.json()
        assert log["report_key"].endswith(".pdf")
        assert log["webhook"] is None
        assert log["drift_status"] in ("stable", "moderate", "critical")

        detail2 = client.get(f"/api/v1/reports/schedules/{schedule_id}").json()
        assert detail2["executions_count"] == 1
        assert detail2["last_status"] == "ok"

        last = client.get(f"/api/v1/reports/schedules/{schedule_id}/last-report")
        assert last.status_code == 200 and last.content.startswith(b"%PDF")

        logs = client.get("/api/v1/reports/schedules/logs")
        assert logs.status_code == 200 and len(logs.json()) >= 1

        deleted = client.delete(f"/api/v1/reports/schedules/{schedule_id}")
        assert deleted.status_code == 200 and deleted.json()["deleted"] is True
        assert client.get("/api/v1/reports/schedules").json()["total"] == 0
        assert client.get(f"/api/v1/reports/schedules/{schedule_id}").status_code == 404

    def test_programacion_html_genera_html(self):
        run_id = _completed_run_id()
        create = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "report_format": "html", "interval_minutes": 60},
        )
        schedule_id = create.json()["schedule_id"]
        log = client.post(f"/api/v1/reports/schedules/{schedule_id}/run-now").json()
        assert log["report_key"].endswith(".html")
        last = client.get(f"/api/v1/reports/schedules/{schedule_id}/last-report")
        assert "<html" in last.text.lower()

    def test_last_report_404_sin_ejecuciones(self):
        run_id = _completed_run_id()
        create = client.post("/api/v1/reports/schedules", json={"run_id": run_id})
        schedule_id = create.json()["schedule_id"]
        res = client.get(f"/api/v1/reports/schedules/{schedule_id}/last-report")
        assert res.status_code == 404 and res.json()["code"] == "REPORT_NOT_GENERATED"

    def test_programar_run_inexistente_404(self):
        res = client.post("/api/v1/reports/schedules", json={"run_id": "RUN-FANTASMA"})
        assert res.status_code == 404 and res.json()["code"] == "RUN_NOT_FOUND"

    def test_intervalo_fuera_de_rango_422(self):
        run_id = _completed_run_id()
        res = client.post("/api/v1/reports/schedules", json={"run_id": run_id, "interval_minutes": 1})
        assert res.status_code == 422


class TestWebhookGovernance:
    def test_webhook_ip_privada_bloqueado_en_alta(self):
        run_id = _completed_run_id()
        res = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "webhook_url": "http://192.168.1.1/hook"},
        )
        assert res.status_code == 400
        assert res.json()["code"] == "SSRF_BLOCKED_IP"

    def test_webhook_metadata_gcp_bloqueado_en_alta(self):
        run_id = _completed_run_id()
        res = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "webhook_url": "http://169.254.169.254/computeMetadata/v1/"},
        )
        assert res.status_code == 400
        assert res.json()["code"] == "SSRF_BLOCKED_IP"

    def test_webhook_esquema_no_http_rechazado(self):
        run_id = _completed_run_id()
        res = client.post(
            "/api/v1/reports/schedules", json={"run_id": run_id, "webhook_url": "ftp://example.com/hook"}
        )
        assert res.status_code == 400
        assert res.json()["code"] == "INVALID_URL_SCHEME"

    def test_trigger_always_entrega_siempre(self, monkeypatch):
        captured = []

        async def fake_send(url, payload):
            captured.append((url, payload))
            return WebhookDeliveryResult(delivered=True, reason="delivered", http_status=200)

        monkeypatch.setattr(ReportService, "send_webhook", staticmethod(fake_send))
        run_id = _completed_run_id()
        create = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "webhook_url": PUBLIC_WEBHOOK_URL, "trigger": "always", "report_format": "pdf"},
        )
        schedule_id = create.json()["schedule_id"]
        log = client.post(f"/api/v1/reports/schedules/{schedule_id}/run-now").json()
        assert log["webhook"]["delivered"] is True
        assert len(captured) == 1
        url, payload = captured[0]
        assert url == PUBLIC_WEBHOOK_URL
        assert payload["event"] == "dataflow.executive_report.regenerated"
        assert payload["run_id"] == run_id
        assert payload["report_attachment"]["content_base64"]
        assert payload["governance"]
        detail = client.get(f"/api/v1/reports/schedules/{schedule_id}").json()
        assert detail["deliveries_count"] == 1

    def test_trigger_critical_drift_solo_entrega_si_hay_drift_critico(self, monkeypatch):
        captured = []

        async def fake_send(url, payload):
            captured.append(payload)
            return WebhookDeliveryResult(delivered=True, reason="delivered", http_status=200)

        monkeypatch.setattr(ReportService, "send_webhook", staticmethod(fake_send))
        run_id = _completed_run_id()
        create = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "webhook_url": PUBLIC_WEBHOOK_URL, "trigger": "critical_drift"},
        )
        schedule_id = create.json()["schedule_id"]
        log = client.post(f"/api/v1/reports/schedules/{schedule_id}/run-now").json()
        detail = client.get(f"/api/v1/reports/schedules/{schedule_id}").json()
        # Entrega coherente con el estado de drift real del run
        if detail["last_drift_status"] == "critical":
            assert log["webhook"]["delivered"] is True and len(captured) == 1
        else:
            assert log["webhook"] is None and len(captured) == 0
            assert detail["last_status"] == "ok"  # reporte generado igualmente

    def test_fallo_de_entrega_no_rompe_la_programacion(self, monkeypatch):
        async def failing_send(url, payload):
            return WebhookDeliveryResult(delivered=False, reason="network_error", error="timeout simulado")

        monkeypatch.setattr(ReportService, "send_webhook", staticmethod(failing_send))
        run_id = _completed_run_id()
        create = client.post(
            "/api/v1/reports/schedules",
            json={"run_id": run_id, "webhook_url": PUBLIC_WEBHOOK_URL, "trigger": "always"},
        )
        schedule_id = create.json()["schedule_id"]
        log = client.post(f"/api/v1/reports/schedules/{schedule_id}/run-now").json()
        assert log["webhook"]["delivered"] is False
        detail = client.get(f"/api/v1/reports/schedules/{schedule_id}").json()
        assert detail["last_status"] == "delivery_failed"
        assert detail["executions_count"] == 1  # el reporte sí se generó
        assert detail["deliveries_count"] == 0


class TestSchedulerLoop:
    def test_run_due_schedules_solo_ejecuta_vencidas(self, monkeypatch):
        async def fake_send(url, payload):
            return WebhookDeliveryResult(delivered=True, reason="delivered", http_status=200)

        monkeypatch.setattr(ReportService, "send_webhook", staticmethod(fake_send))
        run_id = _completed_run_id()
        create = client.post("/api/v1/reports/schedules", json={"run_id": run_id, "interval_minutes": 5})
        schedule_id = create.json()["schedule_id"]
        schedule = REPORT_SCHEDULES[schedule_id]

        # Aún no vencida → no se ejecuta
        logs = asyncio.run(ReportService.run_due_schedules(now=datetime.now(timezone.utc)))
        assert logs == []
        assert schedule.executions_count == 0

        # Vencida → se ejecuta y reprograma en el futuro
        schedule.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        logs = asyncio.run(ReportService.run_due_schedules())
        assert len(logs) == 1
        assert schedule.executions_count == 1
        assert schedule.next_run_at > datetime.now(timezone.utc)

        # Segunda pasada inmediata → no vuelve a ejecutar
        logs2 = asyncio.run(ReportService.run_due_schedules())
        assert logs2 == []
        assert schedule.executions_count == 1

    def test_programacion_deshabilitada_no_ejecuta(self):
        run_id = _completed_run_id()
        create = client.post("/api/v1/reports/schedules", json={"run_id": run_id, "interval_minutes": 5})
        schedule_id = create.json()["schedule_id"]
        schedule = REPORT_SCHEDULES[schedule_id]
        schedule.enabled = False
        schedule.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        logs = asyncio.run(ReportService.run_due_schedules())
        assert logs == []
        assert schedule.executions_count == 0

    def test_send_webhook_real_contra_url_invalida_devuelve_error_sin_excepcion(self):
        # validación SSRF falla (IP privada) → resultado estructurado, no excepción
        result = asyncio.run(ReportService.send_webhook("http://10.0.0.1/hook", {"event": "test"}))
        assert result.delivered is False
        assert result.reason == "ssrf_validation_failed"
