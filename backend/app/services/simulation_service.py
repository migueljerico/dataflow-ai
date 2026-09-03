"""
Servicio de simulación interactiva de transformaciones hipotéticas (v1.16.0).

Aplica los pasos propuestos sobre una COPIA efímera del dataset y calcula el
análisis de drift por percentiles resultante (raw vs simulado), sin modificar
el dataset original, sin crear ejecuciones ni tocar el historial de runs.

Gobernanza: cada paso se valida contra TransformationRegistry exactamente igual
que en la ejecución real; los pasos inválidos se reportan por paso sin abortar
la simulación completa (feedback interactivo en tiempo real para el usuario).
"""

import time
from typing import List

import pandas as pd

from app.core.exceptions import FunctionalException
from app.models.etl import TransformationStep
from app.models.simulation import (
    MAX_SIMULATION_STEPS,
    DriftSimulationResult,
    SimulatedStepOutcome,
)
from app.services.dataset_service import DatasetService
from app.services.drift_service import DriftService
from app.transformations.registry import TransformationRegistry


class SimulationService:
    @staticmethod
    def simulate_drift(dataset_id: str, steps: List[TransformationStep]) -> DriftSimulationResult:
        """Simula el impacto de transformaciones hipotéticas sobre los percentiles de drift."""
        if len(steps) > MAX_SIMULATION_STEPS:
            raise FunctionalException(
                message=f"La simulación acepta como máximo {MAX_SIMULATION_STEPS} pasos por consulta.",
                code="TOO_MANY_SIMULATION_STEPS",
                status_code=400,
            )

        raw_df: pd.DataFrame = DatasetService.load_dataframe(dataset_id)
        df_sim = raw_df.copy()
        rows_before, columns_before = raw_df.shape

        started = time.perf_counter()
        outcomes: List[SimulatedStepOutcome] = []
        applied_count = 0

        for step in steps:
            outcome = SimulatedStepOutcome(
                step_id=step.step_id, operation=step.operation, column=step.column, applied=False
            )
            try:
                transformation = TransformationRegistry.validate_operation_and_parameters(
                    step.operation, df_sim, step.parameters
                )
                result = transformation.apply(df_sim, step.parameters)
                df_sim = result[0] if isinstance(result, tuple) else result
                outcome.applied = True
                outcome.rows_affected = int(result[1]) if isinstance(result, tuple) else len(df_sim)
                applied_count += 1
            except Exception as exc:  # un paso inválido no aborta la simulación interactiva
                outcome.error = str(exc)[:200]
            outcomes.append(outcome)

        # Drift del dataset simulado contra el raw original (misma semántica que un run real)
        drift_report = DriftService.analyze_drift(clean_df=df_sim, raw_df=raw_df)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        rows_after, columns_after = df_sim.shape
        return DriftSimulationResult(
            dataset_id=dataset_id,
            hypothetical_steps=len(steps),
            applied_steps=applied_count,
            step_outcomes=outcomes,
            rows_before=rows_before,
            rows_after=rows_after,
            columns_before=columns_before,
            columns_after=columns_after,
            drift_report=drift_report,
            elapsed_ms=elapsed_ms,
        )
