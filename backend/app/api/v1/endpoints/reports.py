"""
Endpoints de reportes ejecutivos (PDF/HTML), exportación programada y webhooks.

Gobernanza: las programaciones y webhooks los crea explícitamente el usuario;
la URL del webhook se valida contra SSRF en el alta y en cada envío.
"""

from typing import List

from app.core.exceptions import FunctionalException
from app.core.storage import get_storage
from app.models.report import (
    ReportFormatEnum,
    ReportSchedule,
    ReportScheduleCreate,
    ReportScheduleListResponse,
    ScheduleExecutionLog,
)
from app.services.report_service import REPORT_SCHEDULES, SCHEDULE_LOGS, ReportService
from fastapi import APIRouter, Query, Response, status
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/{run_id}/pdf")
async def export_executive_report_pdf(run_id: str, lang: str = Query("es", description="Idioma del reporte (es, en)")):
    """Descargar el reporte ejecutivo de la ejecución en PDF (generación determinista)."""
    sanitized_lang = lang if lang in ("es", "en") else "es"
    pdf_bytes = ReportService.generate_pdf_report(run_id, lang=sanitized_lang)
    safe_run_id = run_id.replace("/", "_").replace("\\", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reporte_ejecutivo_{safe_run_id}.pdf"'},
    )


@router.get("/{run_id}/html")
async def export_executive_report_html(run_id: str, lang: str = Query("es", description="Idioma del reporte (es, en)")):
    """Descargar el reporte ejecutivo de la ejecución en HTML autocontenido."""
    sanitized_lang = lang if lang in ("es", "en") else "es"
    html_content = ReportService.generate_html_report(run_id, lang=sanitized_lang)
    safe_run_id = run_id.replace("/", "_").replace("\\", "_")
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="reporte_ejecutivo_{safe_run_id}.html"'},
    )


@router.post("/schedules", response_model=ReportSchedule, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(req: ReportScheduleCreate):
    """
    Crear una exportación programada (ejecución desatendida) del reporte ejecutivo.
    Si se aporta webhook_url, se valida contra SSRF antes de registrarla.
    """
    return ReportService.create_schedule(req)


@router.get("/schedules", response_model=ReportScheduleListResponse)
async def list_report_schedules():
    """Listar las exportaciones programadas activas y su último estado."""
    schedules = ReportService.list_schedules()
    return ReportScheduleListResponse(schedules=schedules, total=len(schedules))


@router.get("/schedules/logs", response_model=List[ScheduleExecutionLog])
async def list_schedule_logs(limit: int = Query(20, ge=1, le=200)):
    """Historial de ejecuciones desatendidas (regeneraciones y entregas de webhook)."""
    return SCHEDULE_LOGS[:limit]


@router.get("/schedules/{schedule_id}", response_model=ReportSchedule)
async def get_report_schedule(schedule_id: str):
    """Detalle de una programación."""
    return ReportService.get_schedule(schedule_id)


@router.post("/schedules/{schedule_id}/run-now", response_model=ScheduleExecutionLog)
async def run_report_schedule_now(schedule_id: str):
    """Forzar la regeneración inmediata del reporte (y entrega según trigger)."""
    schedule = ReportService.get_schedule(schedule_id)
    return await ReportService.execute_schedule(schedule)


@router.get("/schedules/{schedule_id}/last-report")
async def download_last_scheduled_report(schedule_id: str):
    """Descargar el último reporte generado por la programación."""
    schedule = ReportService.get_schedule(schedule_id)
    if not schedule.last_report_key:
        raise FunctionalException(
            message="La programación aún no ha generado ningún reporte.",
            code="REPORT_NOT_GENERATED",
            status_code=404,
        )
    storage = get_storage()
    if not storage.exists(schedule.last_report_key):
        raise FunctionalException(
            message="El último reporte generado ya no está disponible en el almacenamiento.",
            code="REPORT_NOT_FOUND",
            status_code=404,
        )
    content = storage.read_file(schedule.last_report_key)
    is_pdf = schedule.report_format == ReportFormatEnum.PDF
    media_type = "application/pdf" if is_pdf else "text/html; charset=utf-8"
    ext = "pdf" if is_pdf else "html"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="reporte_programado_{schedule_id}.{ext}"'},
    )


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_200_OK)
async def delete_report_schedule(schedule_id: str):
    """Eliminar una exportación programada."""
    ReportService.delete_schedule(schedule_id)
    return {"deleted": True, "schedule_id": schedule_id, "remaining": len(REPORT_SCHEDULES)}
