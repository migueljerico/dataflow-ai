import html
import re

from app.core.exceptions import FunctionalException
from app.models.analytics import ExecutiveAnalyticsReport
from app.services.analytics_service import AnalyticsService
from fastapi import APIRouter, Path, Query, Response

router = APIRouter()

ALLOWED_LANGUAGES = {"es", "en", "zh", "hi", "fr", "ar", "bn", "pt", "id", "ur", "ru", "de", "ja"}
RUN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


@router.get("/{run_id}", response_model=ExecutiveAnalyticsReport)
async def get_business_analytics(run_id: str = Path(..., description="ID de la ejecución")):
    """
    Obtener el reporte ejecutivo de Business Analytics y KPIs calculados con pandas
    sobre el dataset limpio de la ejecución 'run_id'.
    """
    if not RUN_ID_REGEX.match(run_id):
        raise FunctionalException(
            message=f"El identificador de ejecución '{run_id}' contiene caracteres no permitidos.",
            code="INVALID_RUN_ID",
            status_code=400,
        )
    return AnalyticsService.generate_report(run_id)


@router.get("/{run_id}/export")
async def export_business_analytics(
    run_id: str = Path(..., description="ID de la ejecución"),
    lang: str = Query("es", description="Código de idioma para el reporte (es, en, etc.)"),
):
    """
    Exportar el reporte ejecutivo de Business Analytics con gráficos vectoriales SVG
    en formato HTML interactivo preparado para impresión directa a PDF (A4).
    """
    if not RUN_ID_REGEX.match(run_id):
        raise FunctionalException(
            message=f"El identificador de ejecución '{run_id}' contiene caracteres no permitidos.",
            code="INVALID_RUN_ID",
            status_code=400,
        )
    sanitized_lang = lang.strip().lower() if lang else "es"
    if sanitized_lang not in ALLOWED_LANGUAGES:
        sanitized_lang = "es"

    safe_run_id = html.escape(run_id)
    html_content = AnalyticsService.generate_html_report(run_id, lang=sanitized_lang)
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_ejecutivo_{safe_run_id}.html"',
            "X-Content-Type-Options": "nosniff",
        },
    )
