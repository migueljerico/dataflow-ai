from fastapi import APIRouter
from app.models.analytics import ExecutiveAnalyticsReport
from app.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/{run_id}", response_model=ExecutiveAnalyticsReport)
async def get_business_analytics(run_id: str):
    """
    Obtener el reporte ejecutivo de Business Analytics y KPIs calculados con pandas
    sobre el dataset limpio de la ejecución 'run_id'.
    """
    return AnalyticsService.generate_report(run_id)
