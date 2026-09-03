"""
Endpoint de simulación interactiva de transformaciones hipotéticas (v1.16.0).

Permite anticipar el efecto de los pasos del plan sobre los percentiles de drift
en tiempo real, ANTES de la aprobación formal. La simulación no modifica el
dataset, no crea ejecuciones ni altera el historial (gobernanza estricta).
"""

from app.models.simulation import DriftSimulationRequest, DriftSimulationResult
from app.services.simulation_service import SimulationService
from fastapi import APIRouter

router = APIRouter()


@router.post("/drift", response_model=DriftSimulationResult)
async def simulate_drift(req: DriftSimulationRequest):
    """
    Simular transformaciones hipotéticas sobre el dataset y devolver el análisis
    de drift por percentiles resultante (raw vs simulado), con el resultado de
    validación paso a paso contra TransformationRegistry.
    """
    return SimulationService.simulate_drift(req.dataset_id, req.steps)
