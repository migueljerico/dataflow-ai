"""
Modelos de la simulación interactiva de transformaciones hipotéticas (v1.16.0).

La simulación permite anticipar el impacto de un conjunto de transformaciones
sobre los percentiles de drift ANTES de la aprobación formal del plan.
Gobernanza: la simulación es puramente hipotética — no modifica el dataset,
no crea ejecuciones ni entra en el historial de runs.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.analytics import DriftAnalysisReport
from app.models.etl import TransformationStep, utc_now

MAX_SIMULATION_STEPS = 50


class DriftSimulationRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset sobre el que se simula")
    steps: List[TransformationStep] = Field(
        default_factory=list,
        description=f"Pasos hipotéticos (máx. {MAX_SIMULATION_STEPS}), validados contra el Registry",
    )


class SimulatedStepOutcome(BaseModel):
    step_id: str
    operation: str
    column: Optional[str] = None
    applied: bool
    rows_affected: int = 0
    error: Optional[str] = None


class DriftSimulationResult(BaseModel):
    dataset_id: str
    simulated: bool = True
    governance_note: str = (
        "SIMULACIÓN HIPOTÉTICA: el dataset no se modifica, no se crea ninguna ejecución "
        "ni se registra en el historial. La aprobación formal sigue requiriendo el flujo "
        "de gobernanza completo (reconciliación contra el plan canónico)."
    )
    hypothetical_steps: int
    applied_steps: int
    step_outcomes: List[SimulatedStepOutcome] = Field(default_factory=list)
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    drift_report: DriftAnalysisReport
    elapsed_ms: float
    generated_at: datetime = Field(default_factory=utc_now)
