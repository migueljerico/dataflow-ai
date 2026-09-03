"""
Simulación interactiva de transformaciones hipotéticas sobre percentiles de drift (v1.16.0).

Gobernanza verificada: la simulación NO modifica el dataset, NO crea ejecuciones
ni alimenta el historial de runs; los pasos se validan contra TransformationRegistry
y los inválidos se reportan por paso sin abortar la simulación.
"""

import pandas as pd
from fastapi.testclient import TestClient
from pandas.testing import assert_frame_equal

from app.main import app
from app.services.dataset_service import DatasetService
from app.services.etl_service import RUNS_HISTORY
from app.services.simulation_service import SimulationService

client = TestClient(app)


def _load_sales_dataset() -> str:
    res = client.post("/api/v1/datasets/samples/sales/load")
    assert res.status_code == 201
    return res.json()["dataset_id"]


def _sim_step(step_id, operation, column=None, parameters=None, reason="simulación"):
    return {
        "step_id": step_id,
        "operation": operation,
        "column": column,
        "parameters": parameters if parameters is not None else ({"column": column} if column else {}),
        "reason": reason,
        "status": "proposed",
    }


class TestDriftSimulationEndpoint:
    def test_simulacion_sin_pasos_devuelve_baseline(self):
        dataset_id = _load_sales_dataset()
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": dataset_id, "steps": []})
        assert res.status_code == 200
        body = res.json()
        assert body["simulated"] is True
        assert "SIMULACIÓN HIPOTÉTICA" in body["governance_note"]
        assert body["hypothetical_steps"] == 0
        assert body["rows_before"] == body["rows_after"]
        drift = body["drift_report"]
        assert drift["overall_drift_status"] == "stable"
        assert isinstance(drift["columns"], list)

    def test_simulacion_con_pasos_validos(self):
        dataset_id = _load_sales_dataset()
        steps = [
            _sim_step("SIM-001", "trim_text", "Nombre_Cliente"),
            _sim_step("SIM-002", "convert_numeric", "Precio_Unidad"),
        ]
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": dataset_id, "steps": steps})
        assert res.status_code == 200
        body = res.json()
        assert body["applied_steps"] == 2
        assert all(o["applied"] for o in body["step_outcomes"])
        # El drift compara simulado vs raw: la conversión numérica activa percentiles
        precio = next((c for c in body["drift_report"]["columns"] if c["column_name"] == "Precio_Unidad"), None)
        assert precio is not None
        assert precio["clean_percentiles"] is not None
        assert body["elapsed_ms"] >= 0

    def test_paso_invalido_no_aborta_la_simulacion(self):
        dataset_id = _load_sales_dataset()
        steps = [
            _sim_step("SIM-MALO", "drop_database", None, {}),
            _sim_step("SIM-OK", "trim_text", "Nombre_Cliente"),
        ]
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": dataset_id, "steps": steps})
        assert res.status_code == 200
        body = res.json()
        outcomes = {o["step_id"]: o for o in body["step_outcomes"]}
        assert outcomes["SIM-MALO"]["applied"] is False
        assert "no está contemplada" in outcomes["SIM-MALO"]["error"]
        assert outcomes["SIM-OK"]["applied"] is True
        assert body["applied_steps"] == 1

    def test_parametro_no_permitido_queda_registrado(self):
        dataset_id = _load_sales_dataset()
        steps = [_sim_step("SIM-X", "trim_text", "Nombre_Cliente", {"column": "Nombre_Cliente", "hack": True})]
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": dataset_id, "steps": steps})
        assert res.status_code == 200
        outcome = res.json()["step_outcomes"][0]
        assert outcome["applied"] is False
        assert "hack" in outcome["error"]

    def test_dataset_inexistente_404(self):
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": "DS-NOEXISTE", "steps": []})
        assert res.status_code == 404

    def test_exceso_de_pasos_400(self):
        dataset_id = _load_sales_dataset()
        steps = [_sim_step(f"SIM-{i}", "trim_text", "Nombre_Cliente") for i in range(51)]
        res = client.post("/api/v1/simulations/drift", json={"dataset_id": dataset_id, "steps": steps})
        assert res.status_code == 400
        assert res.json()["code"] == "TOO_MANY_SIMULATION_STEPS"


class TestSimulationGovernance:
    def test_no_modifica_dataset_ni_crea_ejecuciones(self):
        dataset_id = _load_sales_dataset()
        raw_before: pd.DataFrame = DatasetService.load_dataframe(dataset_id)
        snapshot = raw_before.copy(deep=True)
        history_before = len(RUNS_HISTORY)

        # Simulación con paso agresivo (drop_column) sobre una copia efímera
        from app.models.etl import TransformationStep

        steps = [
            TransformationStep(
                step_id="SIM-DEL",
                operation="drop_column",
                column="Canal",
                parameters={"column": "Canal"},
                reason="hipotética",
            )
        ]
        result = SimulationService.simulate_drift(dataset_id, steps)
        assert result.columns_after == result.columns_before - 1

        # El dataset original permanece intacto
        raw_after = DatasetService.load_dataframe(dataset_id)
        assert_frame_equal(snapshot, raw_after)
        # No se creó ninguna ejecución ni entrada en el historial
        assert len(RUNS_HISTORY) == history_before
