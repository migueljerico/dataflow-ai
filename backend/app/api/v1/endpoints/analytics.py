from app.models.analytics import ExecutiveAnalyticsReport
from app.services.analytics_service import AnalyticsService
from fastapi import APIRouter, Query, Response

router = APIRouter()


@router.get("/{run_id}", response_model=ExecutiveAnalyticsReport)
async def get_business_analytics(run_id: str):
    """
    Obtener el reporte ejecutivo de Business Analytics y KPIs calculados con pandas
    sobre el dataset limpio de la ejecución 'run_id'.
    """
    return AnalyticsService.generate_report(run_id)


@router.get("/{run_id}/export")
async def export_business_analytics(
    run_id: str,
    lang: str = Query("es", description="Código de idioma para el reporte (es, en, etc.)"),
):
    """
    Exportar el reporte ejecutivo de Business Analytics con gráficos vectoriales SVG
    en formato HTML interactivo preparado para impresión directa a PDF (A4).
    """
    html_content = AnalyticsService.generate_html_report(run_id, lang=lang)
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_ejecutivo_{run_id}.html"',
        },
    )
