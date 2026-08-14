from fastapi import APIRouter
from app.models.quality import QualityReport
from app.services.quality_service import QualityService

router = APIRouter()

@router.get("/{dataset_id}/quality", response_model=QualityReport)
async def get_quality(dataset_id: str):
    """
    Obtener el análisis de Data Quality y el Data Quality Score (0-100)
    con el desglose explicable por las 5 dimensiones.
    """
    return QualityService.get_quality_report(dataset_id)
