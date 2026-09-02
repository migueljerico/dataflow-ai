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


@router.get("/{run_id}/export/tmdl")
async def export_tmdl_definition(
    run_id: str = Path(..., description="ID de la ejecución"),
):
    """
    Exportar la definición de tabla y medidas en formato TMDL (Tabular Model Definition Language)
    para Power BI Desktop Developer Mode y Fabric.
    """
    if not RUN_ID_REGEX.match(run_id):
        raise FunctionalException(
            message=f"El identificador de ejecución '{run_id}' contiene caracteres no permitidos.",
            code="INVALID_RUN_ID",
            status_code=400,
        )
    safe_run_id = html.escape(run_id)
    tmdl_content = AnalyticsService.generate_tmdl(run_id)
    return Response(
        content=tmdl_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="modelo_powerbi_{safe_run_id}.tmdl"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{run_id}/export/dax")
async def export_dax_measures_script(
    run_id: str = Path(..., description="ID de la ejecución"),
):
    """
    Exportar el script de medidas DAX calculadas (.dax) para Power BI / DAX Studio / Tabular Editor.
    """
    if not RUN_ID_REGEX.match(run_id):
        raise FunctionalException(
            message=f"El identificador de ejecución '{run_id}' contiene caracteres no permitidos.",
            code="INVALID_RUN_ID",
            status_code=400,
        )
    safe_run_id = html.escape(run_id)
    dax_content = AnalyticsService.generate_dax_script(run_id)
    return Response(
        content=dax_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="medidas_powerbi_{safe_run_id}.dax"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{run_id}/export/pbip")
@router.get("/{run_id}/export/powerbi-project")
async def export_powerbi_pbip_project(
    run_id: str = Path(..., description="ID de la ejecución"),
):
    """
    Exportar el proyecto completo de Power BI Desktop Developer Mode (.pbip) en un archivo ZIP,
    conteniendo el modelo semántico con formato TMDL listo para abrir directamente.
    """
    if not RUN_ID_REGEX.match(run_id):
        raise FunctionalException(
            message=f"El identificador de ejecución '{run_id}' contiene caracteres no permitidos.",
            code="INVALID_RUN_ID",
            status_code=400,
        )
    safe_run_id = html.escape(run_id)
    zip_bytes = AnalyticsService.generate_powerbi_pbip_zip(run_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="proyecto_powerbi_{safe_run_id}.zip"',
            "X-Content-Type-Options": "nosniff",
        },
    )
