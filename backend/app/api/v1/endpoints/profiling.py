from app.models.profiling import ProfilingReport
from app.services.profiler_service import ProfilerService
from fastapi import APIRouter

router = APIRouter()


@router.get("/{dataset_id}/profiling", response_model=ProfilingReport)
async def get_profiling(dataset_id: str):
    """
    Obtener el informe de profiling automático de un dataset por su ID.
    Genera el perfil si aún no ha sido calculado.
    """
    return ProfilerService.get_profiling_report(dataset_id)
