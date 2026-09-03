"""
Servicio de reportes ejecutivos programados y notificaciones webhook (v1.16.0).

Funcionalidades:
- Generación determinista de reportes ejecutivos en PDF (fpdf2) y HTML a partir
  de una ejecución ETL completada (ExecutiveAnalyticsReport + calidad + drift).
- Registro de programaciones (in-memory, coherente con la arquitectura MVP del
  resto de cachés) con regeneración periódica desatendida.
- Notificaciones webhook con protección SSRF/IP-Pinning reutilizando
  app.core.security_url: la URL se valida en el alta y en cada envío.

Gobernanza: "La IA propone, el usuario decide, Python ejecuta." Las schedule y
los webhooks siempre los configura explícitamente el usuario; el bucle de
programación no crea ejecuciones ETL nuevas, solo regenera reportes de runs ya
aprobados y ejecutados.
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx
from fpdf import FPDF

from app.core.exceptions import FunctionalException
from app.core.security_url import PinnedAsyncHTTPTransport, validate_and_resolve_url
from app.core.storage import get_storage
from app.models.analytics import DriftAlertSeverityEnum, ExecutiveAnalyticsReport
from app.models.etl import ExecutionResult
from app.models.report import (
    ReportFormatEnum,
    ReportSchedule,
    ReportScheduleCreate,
    ScheduleExecutionLog,
    WebhookDeliveryResult,
    WebhookTriggerEnum,
)
from app.services.analytics_service import AnalyticsService
from app.services.etl_service import ETLService

logger = logging.getLogger("dataflow.reports")

REPORT_SCHEDULES: Dict[str, ReportSchedule] = {}
SCHEDULE_LOGS: List[ScheduleExecutionLog] = []
SCHEDULER_TICK_SECONDS = 15.0
WEBHOOK_TIMEOUT_SECONDS = 10.0

_LABELS = {
    "es": {
        "title": "DataFlow AI — Reporte Ejecutivo",
        "run": "Ejecución",
        "dataset": "Dataset",
        "generated": "Generado",
        "summary": "Resumen ejecutivo",
        "kpis": "Indicadores clave (KPIs)",
        "quality": "Calidad de datos (antes vs después)",
        "score_before": "Score antes",
        "score_after": "Score después",
        "delta": "Delta",
        "rows_before": "Filas antes",
        "rows_after": "Filas después",
        "steps": "Transformaciones aplicadas",
        "drift": "Análisis de drift por percentiles",
        "drift_overall": "Estado global",
        "drift_counts": "Columnas estables / moderadas / críticas",
        "drift_alerts": "Alertas de drift (top 5)",
        "recommendations": "Recomendaciones estratégicas",
        "governance": "Gobernanza: La IA propone, el usuario decide, Python ejecuta.",
        "page": "Página",
        "no_data": "Sin datos disponibles",
        "schedule": "Exportación programada",
    },
    "en": {
        "title": "DataFlow AI — Executive Report",
        "run": "Run",
        "dataset": "Dataset",
        "generated": "Generated",
        "summary": "Executive summary",
        "kpis": "Key performance indicators (KPIs)",
        "quality": "Data quality (before vs after)",
        "score_before": "Score before",
        "score_after": "Score after",
        "delta": "Delta",
        "rows_before": "Rows before",
        "rows_after": "Rows after",
        "steps": "Applied transformations",
        "drift": "Percentile drift analysis",
        "drift_overall": "Overall status",
        "drift_counts": "Stable / moderate / critical columns",
        "drift_alerts": "Drift alerts (top 5)",
        "recommendations": "Strategic recommendations",
        "governance": "Governance: AI proposes, the user decides, Python executes.",
        "page": "Page",
        "no_data": "No data available",
        "schedule": "Scheduled export",
    },
}


def _labels(lang: str) -> Dict[str, str]:
    return _LABELS.get(lang, _LABELS["es"])


def _pdf_safe(text: str) -> str:
    """Las fuentes core de fpdf2 usan latin-1: sustituye caracteres no soportados."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _make_executive_pdf(page_label: str) -> FPDF:
    """PDF con pie de página numerado (patrón footer() documentado de fpdf2)."""

    class _ExecutivePDF(FPDF):
        def footer(self):  # noqa: D102 — hook de fpdf2
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(107, 114, 128)
            text = f"{page_label} {self.page_no()}/" + "{nb}"
            self.cell(0, 5, _pdf_safe(text), align="C")

    pdf = _ExecutivePDF(format="A4")
    pdf.alias_nb_pages()
    return pdf


class ReportService:
    @staticmethod
    def generate_pdf_report(run_id: str, lang: str = "es") -> bytes:
        """Genera el reporte ejecutivo en PDF de forma determinista a partir del run."""
        lab = _labels(lang)
        report: ExecutiveAnalyticsReport = AnalyticsService.generate_report(run_id)
        result: ExecutionResult = ETLService.get_run_result(run_id)

        comparison = None
        try:
            comparison = ETLService.get_quality_comparison(run_id)
        except FunctionalException:
            comparison = None

        pdf = _make_executive_pdf(lab["page"])
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        # Cabecera
        pdf.set_fill_color(37, 99, 235)
        pdf.rect(0, 0, 210, 26, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(10, 8)
        pdf.cell(0, 10, _pdf_safe(lab["title"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        pdf.set_x(10)
        pdf.cell(
            0,
            6,
            _pdf_safe(
                f"{lab['run']}: {report.run_id}  |  {lab['dataset']}: {report.dataset_name}  |  {lab['generated']}: {generated_at}"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_y(34)
        pdf.set_text_color(17, 24, 39)

        def section(title: str) -> None:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(37, 99, 235)
            pdf.cell(0, 8, _pdf_safe(title), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(17, 24, 39)
            pdf.set_draw_color(229, 231, 235)
            y = pdf.get_y()
            pdf.line(10, y, 200, y)
            pdf.ln(2)

        def body(text: str) -> None:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.5, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)

        # Resumen ejecutivo
        section(lab["summary"])
        body(report.executive_summary or lab["no_data"])

        # KPIs
        if report.kpis:
            section(lab["kpis"])
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(243, 244, 246)
            pdf.cell(70, 7, _pdf_safe("KPI"), border=1, fill=True)
            pdf.cell(40, 7, _pdf_safe("Valor"), border=1, fill=True)
            pdf.cell(0, 7, _pdf_safe("Contexto"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for kpi in report.kpis[:12]:
                pdf.cell(70, 6.5, _pdf_safe(kpi.title), border=1)
                pdf.cell(40, 6.5, _pdf_safe(kpi.value), border=1)
                pdf.cell(0, 6.5, _pdf_safe(kpi.subtitle), border=1, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # Calidad antes vs después
        section(lab["quality"])
        if comparison is not None:
            pdf.set_font("Helvetica", "", 10)
            body(
                f"{lab['score_before']}: {comparison.overall_score_before}  |  "
                f"{lab['score_after']}: {comparison.overall_score_after}  |  "
                f"{lab['delta']}: {comparison.delta_score:+.2f}"
            )
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(243, 244, 246)
            pdf.cell(70, 7, _pdf_safe("Dimensión"), border=1, fill=True)
            pdf.cell(40, 7, _pdf_safe("Antes"), border=1, fill=True)
            pdf.cell(40, 7, _pdf_safe("Después"), border=1, fill=True)
            pdf.cell(0, 7, _pdf_safe("Delta"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for dim in comparison.dimensions:
                pdf.cell(
                    70,
                    6.5,
                    _pdf_safe(dim.dimension.value if hasattr(dim.dimension, "value") else str(dim.dimension)),
                    border=1,
                )
                pdf.cell(40, 6.5, _pdf_safe(f"{dim.score_before:.2f}"), border=1)
                pdf.cell(40, 6.5, _pdf_safe(f"{dim.score_after:.2f}"), border=1)
                pdf.cell(0, 6.5, _pdf_safe(f"{dim.delta:+.2f}"), border=1, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        else:
            body(lab["no_data"])
        body(
            f"{lab['rows_before']}: {result.rows_before}  |  {lab['rows_after']}: {result.rows_after}  |  "
            f"{lab['steps']}: {result.applied_steps_count}"
        )

        # Drift
        drift = report.drift_analysis
        section(lab["drift"])
        if drift is not None:
            body(
                f"{lab['drift_overall']}: {drift.overall_drift_status.value.upper()}  |  "
                f"{lab['drift_counts']}: {drift.stable_columns_count} / {drift.moderate_columns_count} / {drift.critical_columns_count}"
            )
            if drift.alerts:
                pdf.set_font("Helvetica", "B", 9)
                for alert in drift.alerts[:5]:
                    pdf.set_font("Helvetica", "B", 9)
                    severity_tag = f"[{alert.severity.value.upper()}]"
                    pdf.multi_cell(
                        0,
                        5.5,
                        _pdf_safe(
                            f"{severity_tag} {alert.column} — {alert.title} ({alert.metric}={alert.value}, umbral={alert.threshold})"
                        ),
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                pdf.ln(1)
        else:
            body(lab["no_data"])

        # Recomendaciones
        if report.strategic_recommendations:
            section(lab["recommendations"])
            for idx, rec in enumerate(report.strategic_recommendations[:6], 1):
                body(f"{idx}. {rec}")

        # Pie de gobernanza
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(107, 114, 128)
        pdf.multi_cell(0, 4.5, _pdf_safe(lab["governance"]), new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    @staticmethod
    def generate_html_report(run_id: str, lang: str = "es") -> str:
        """Delega en el generador HTML ejecutivo existente (AnalyticsService)."""
        return AnalyticsService.generate_html_report(run_id, lang=lang)

    @staticmethod
    def build_webhook_payload(
        schedule: ReportSchedule,
        report: ExecutiveAnalyticsReport,
        result: ExecutionResult,
        drift_status: str,
        report_bytes: bytes,
        report_key: str,
    ) -> Dict:
        """Payload JSON determinista del webhook, con reporte adjunto en base64."""
        drift = report.drift_analysis
        top_alerts = []
        if drift is not None:
            for alert in drift.alerts[:5]:
                top_alerts.append(
                    {
                        "column": alert.column,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "metric": alert.metric,
                        "value": alert.value,
                        "threshold": alert.threshold,
                    }
                )
        comparison = None
        try:
            comp = ETLService.get_quality_comparison(schedule.run_id)
            comparison = {
                "score_before": comp.overall_score_before,
                "score_after": comp.overall_score_after,
                "delta_score": comp.delta_score,
            }
        except FunctionalException:
            comparison = None

        return {
            "event": "dataflow.executive_report.regenerated",
            "schedule_id": schedule.schedule_id,
            "run_id": schedule.run_id,
            "dataset_id": schedule.dataset_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_format": schedule.report_format.value,
            "trigger": schedule.trigger.value,
            "drift": {
                "overall_status": drift_status,
                "critical_columns": drift.critical_columns_count if drift else 0,
                "moderate_columns": drift.moderate_columns_count if drift else 0,
                "total_alerts": drift.total_alerts if drift else 0,
                "critical_alerts": sum(
                    1 for a in (drift.alerts if drift else []) if a.severity == DriftAlertSeverityEnum.CRITICAL
                ),
                "top_alerts": top_alerts,
            },
            "quality": comparison,
            "execution": {
                "rows_before": result.rows_before,
                "rows_after": result.rows_after,
                "applied_steps": result.applied_steps_count,
                "status": result.status,
            },
            "kpi_highlights": [{"title": k.title, "value": k.value} for k in report.kpis[:5]],
            "report_attachment": {
                "filename": report_key,
                "content_base64": base64.b64encode(report_bytes).decode("ascii"),
            },
            "governance": "La IA propone, el usuario decide, Python ejecuta.",
        }

    @staticmethod
    async def send_webhook(url: str, payload: Dict) -> WebhookDeliveryResult:
        """POST JSON al webhook con validación SSRF + IP Pinning en cada envío."""
        try:
            info = validate_and_resolve_url(url)
        except FunctionalException as exc:
            return WebhookDeliveryResult(delivered=False, reason="ssrf_validation_failed", error=exc.message)

        transport = PinnedAsyncHTTPTransport(info["pinned_ip"])
        headers = {
            "Host": info["hostname"],
            "User-Agent": "DataFlow-AI/1.16 (Executive Report Webhook)",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                transport=transport, timeout=WEBHOOK_TIMEOUT_SECONDS, follow_redirects=False
            ) as client:
                response = await client.post(info["safe_url"], json=payload, headers=headers)
            if 200 <= response.status_code < 300:
                return WebhookDeliveryResult(delivered=True, reason="delivered", http_status=response.status_code)
            return WebhookDeliveryResult(
                delivered=False,
                reason="http_error",
                http_status=response.status_code,
                error=f"HTTP {response.status_code}",
            )
        except Exception as exc:  # errores de red no deben tumbar el scheduler
            return WebhookDeliveryResult(delivered=False, reason="network_error", error=str(exc)[:200])

    @staticmethod
    async def execute_schedule(schedule: ReportSchedule) -> ScheduleExecutionLog:
        """Regenera el reporte del run, lo persiste y notifica según el trigger configurado."""
        now = datetime.now(timezone.utc)
        log = ScheduleExecutionLog(
            schedule_id=schedule.schedule_id, executed_at=now, report_format=schedule.report_format
        )
        try:
            report = AnalyticsService.generate_report(schedule.run_id)
            result = ETLService.get_run_result(schedule.run_id)
            drift_status = (
                report.drift_analysis.overall_drift_status.value if report.drift_analysis is not None else "stable"
            )

            if schedule.report_format == ReportFormatEnum.PDF:
                content = ReportService.generate_pdf_report(schedule.run_id, lang=schedule.lang)
                ext = "pdf"
            else:
                content = ReportService.generate_html_report(schedule.run_id, lang=schedule.lang).encode("utf-8")
                ext = "html"

            report_key = f"report_{schedule.schedule_id}_{now.strftime('%Y%m%d%H%M%S')}.{ext}"
            get_storage().save_file(report_key, content)

            schedule.executions_count += 1
            schedule.last_executed_at = now
            schedule.last_drift_status = drift_status
            schedule.last_report_key = report_key
            schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
            log.drift_status = drift_status
            log.report_key = report_key

            should_deliver = bool(schedule.webhook_url) and (
                schedule.trigger == WebhookTriggerEnum.ALWAYS or drift_status == "critical"
            )
            if should_deliver and schedule.webhook_url:
                payload = ReportService.build_webhook_payload(
                    schedule, report, result, drift_status, content, report_key
                )
                delivery = await ReportService.send_webhook(schedule.webhook_url, payload)
                log.webhook = delivery
                if delivery.delivered:
                    schedule.deliveries_count += 1
                    schedule.last_status = "ok"
                    schedule.last_error = None
                else:
                    schedule.last_status = "delivery_failed"
                    schedule.last_error = delivery.error or delivery.reason
            else:
                schedule.last_status = "ok"
                schedule.last_error = None
        except Exception as exc:
            logger.warning("Fallo en schedule %s: %s", schedule.schedule_id, exc)
            schedule.last_status = "error"
            schedule.last_error = str(exc)[:200]
            schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
            log.error = str(exc)[:200]

        SCHEDULE_LOGS.insert(0, log)
        del SCHEDULE_LOGS[200:]
        return log

    @staticmethod
    async def run_due_schedules(now: Optional[datetime] = None) -> List[ScheduleExecutionLog]:
        """Ejecuta las programaciones vencidas. Lo invoca el bucle del scheduler y los tests."""
        current = now or datetime.now(timezone.utc)
        logs: List[ScheduleExecutionLog] = []
        for schedule in list(REPORT_SCHEDULES.values()):
            if not schedule.enabled:
                continue
            if schedule.next_run_at is not None and schedule.next_run_at <= current:
                logs.append(await ReportService.execute_schedule(schedule))
        return logs

    @staticmethod
    async def scheduler_loop() -> None:
        """Bucle desatendido de exportaciones programadas (arranca vía lifespan de FastAPI)."""
        logger.info("Scheduler de reportes ejecutivos iniciado (tick=%.0fs)", SCHEDULER_TICK_SECONDS)
        while True:
            try:
                await ReportService.run_due_schedules()
            except Exception:  # pragma: no cover — red de seguridad del bucle
                logger.exception("Error inesperado en el scheduler de reportes")
            await asyncio.sleep(SCHEDULER_TICK_SECONDS)

    @staticmethod
    def create_schedule(data: ReportScheduleCreate) -> ReportSchedule:
        """Alta de programación: valida run existente y webhook público (anti-SSRF)."""
        result = ETLService.get_run_result(data.run_id)  # 404 RUN_NOT_FOUND si no existe
        if data.webhook_url:
            # Validación SSRF en el alta (DNS + IP pública); se revalida en cada envío
            validate_and_resolve_url(data.webhook_url)
        now = datetime.now(timezone.utc)
        schedule = ReportSchedule(
            schedule_id=f"SCHED-{uuid.uuid4().hex[:8]}",
            run_id=data.run_id,
            dataset_id=result.dataset_id,
            report_format=data.report_format,
            interval_minutes=data.interval_minutes,
            webhook_url=data.webhook_url,
            trigger=data.trigger,
            lang=data.lang if data.lang in _LABELS else "es",
            next_run_at=now + timedelta(minutes=data.interval_minutes),
        )
        REPORT_SCHEDULES[schedule.schedule_id] = schedule
        return schedule

    @staticmethod
    def list_schedules() -> List[ReportSchedule]:
        return sorted(REPORT_SCHEDULES.values(), key=lambda s: s.created_at, reverse=True)

    @staticmethod
    def get_schedule(schedule_id: str) -> ReportSchedule:
        if schedule_id not in REPORT_SCHEDULES:
            raise FunctionalException(
                message=f"La programación '{schedule_id}' no existe.", code="SCHEDULE_NOT_FOUND", status_code=404
            )
        return REPORT_SCHEDULES[schedule_id]

    @staticmethod
    def delete_schedule(schedule_id: str) -> None:
        if schedule_id not in REPORT_SCHEDULES:
            raise FunctionalException(
                message=f"La programación '{schedule_id}' no existe.", code="SCHEDULE_NOT_FOUND", status_code=404
            )
        del REPORT_SCHEDULES[schedule_id]
