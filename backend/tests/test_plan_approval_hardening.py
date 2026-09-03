"""
Gobernanza reforzada de la aprobación de planes (v1.16.0).

Regresión sobre el hueco detectado en revisión externa: el endpoint /approve
ejecutaba los pasos enviados por el cliente sin contrastarlos contra el plan
canónico propuesto. Ahora el servidor hace diff controlado por step_id:
- idéntico → APPROVED (se ejecuta la copia canónica del servidor),
- divergente → EDITED + auditoría [MODIFICADO POR HUMANO] con el diff,
- step_id ajeno al plan → EDITED + auditoría [AÑADIDO POR HUMANO],
- ausente del payload → [OMITIDO],
- duplicados → 400 DUPLICATE_STEP,
- orden de ejecución = orden canónico del plan.
"""

import io

from app.core.exceptions import FunctionalException
from app.models.etl import StepStatusEnum, TransformationPlan, TransformationStep
from app.services.etl_service import ETLService
from fastapi.testclient import TestClient

import pytest

from app.main import app

client = TestClient(app)

SALES_CSV = (
    "Fecha,ID_Cliente,Nombre_Cliente,Producto,Cantidad,Precio_Unidad,Canal,Comercial\n"
    "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
    "2026-01-05,CLI-001, Juan Pérez ,Laptop Pro 15,2, 1200.50 €,Web, Carlos Ruiz \n"
    "06/01/2026,CLI-002,María Gómez,Monitor 4K,1,$350.00,Tienda,Ana Belén\n"
)


def _make_step(step_id="STEP-001", operation="trim_text", column="Nombre", parameters=None, status="proposed"):
    return TransformationStep(
        step_id=step_id,
        operation=operation,
        column=column,
        parameters=parameters if parameters is not None else {"column": column},
        reason="prueba",
        status=status,
    )


def _make_plan(steps):
    return TransformationPlan(plan_id="PLAN-TEST", dataset_id="DS-TEST", summary="plan de prueba", steps=steps)


class TestReconcileReviewedSteps:
    def test_paso_identico_se_aprueba_con_copia_canonica(self):
        canonical = _make_step(parameters={"column": "Nombre"})
        plan = _make_plan([canonical])
        incoming = _make_step(parameters={"column": "Nombre"}, status="approved")
        incoming.reason = "razón manipulada por el cliente"
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [incoming])
        assert len(reviewed) == 1
        assert reviewed[0].status == StepStatusEnum.APPROVED
        # Se ejecuta la copia canónica del servidor, no la del cliente
        assert reviewed[0].reason == "prueba"
        assert any("[PLAN CANÓNICO]" in n and "fingerprint=" in n for n in notes)
        assert not any("[MODIFICADO POR HUMANO]" in n for n in notes)

    def test_parametros_divergentes_marcan_edited_con_diff(self):
        canonical = _make_step(operation="clamp_range", column="Cantidad", parameters={"column": "Cantidad", "min_value": 0})
        plan = _make_plan([canonical])
        incoming = _make_step(
            operation="clamp_range", column="Cantidad", parameters={"column": "Cantidad", "min_value": 5}, status="approved"
        )
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [incoming])
        assert reviewed[0].status == StepStatusEnum.EDITED
        modified = [n for n in notes if "[MODIFICADO POR HUMANO]" in n]
        assert len(modified) == 1
        assert "min_value" in modified[0]
        assert "0" in modified[0] and "5" in modified[0]

    def test_operation_divergente_queda_registrada(self):
        canonical = _make_step(operation="trim_text", column="Nombre")
        plan = _make_plan([canonical])
        incoming = _make_step(step_id="STEP-001", operation="drop_column", column="Nombre", status="approved")
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [incoming])
        assert reviewed[0].status == StepStatusEnum.EDITED
        assert any("trim_text" in n and "drop_column" in n for n in notes if "[MODIFICADO POR HUMANO]" in n)

    def test_rejected_se_mantiene_rechazado(self):
        canonical = _make_step()
        plan = _make_plan([canonical])
        incoming = _make_step(status="rejected")
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [incoming])
        assert reviewed[0].status == StepStatusEnum.REJECTED
        assert not any("[MODIFICADO POR HUMANO]" in n for n in notes)

    def test_paso_canonico_ausente_se_omite_con_nota(self):
        s1 = _make_step(step_id="STEP-001")
        s2 = _make_step(step_id="STEP-002", column="Otra")
        plan = _make_plan([s1, s2])
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [_make_step(step_id="STEP-001", status="approved")])
        assert [s.step_id for s in reviewed] == ["STEP-001"]
        assert any("[OMITIDO]" in n and "STEP-002" in n for n in notes)

    def test_paso_anadido_por_humano_va_al_final_y_queda_registrado(self):
        canonical = _make_step(step_id="STEP-001")
        plan = _make_plan([canonical])
        injected = _make_step(step_id="step-extra", operation="fill_missing", column="Nombre", status="approved")
        reviewed, notes = ETLService.reconcile_reviewed_steps(plan, [injected, _make_step(step_id="STEP-001", status="approved")])
        # Orden canónico primero, añadido al final
        assert [s.step_id for s in reviewed] == ["STEP-001", "step-extra"]
        assert reviewed[1].status == StepStatusEnum.EDITED
        assert any("[AÑADIDO POR HUMANO]" in n and "step-extra" in n for n in notes)

    def test_step_id_duplicado_se_rechaza(self):
        plan = _make_plan([_make_step(step_id="STEP-001")])
        with pytest.raises(FunctionalException) as exc:
            ETLService.reconcile_reviewed_steps(plan, [_make_step(step_id="STEP-001"), _make_step(step_id="STEP-001")])
        assert exc.value.code == "DUPLICATE_STEP"


class TestApproveEndpointHardening:
    def _upload_and_propose(self):
        up = client.post(
            "/api/v1/datasets/upload", files={"file": ("sales_hardening.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")}
        )
        assert up.status_code == 201
        dataset_id = up.json()["dataset_id"]
        plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
        assert plan_res.status_code == 201
        return dataset_id, plan_res.json()

    def test_aprobacion_normal_incluye_fingerprint_del_plan(self):
        _, plan = self._upload_and_propose()
        res = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": plan["steps"]})
        assert res.status_code == 200
        audit = res.json()["audit_logs"]
        assert any("[PLAN CANÓNICO]" in entry and "fingerprint=" in entry for entry in audit)
        assert not any("[MODIFICADO POR HUMANO]" in entry for entry in audit)

    def test_parametros_modificados_dejan_huella_en_auditoria(self):
        _, plan = self._upload_and_propose()
        steps = plan["steps"]
        target = next(s for s in steps if s["operation"] == "convert_numeric")
        target["parameters"] = dict(target["parameters"])
        target["parameters"]["injected_flag"] = True  # parámetro inofensivo fuera de esquema
        res = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": steps})
        assert res.status_code == 200
        body = res.json()
        assert any("[MODIFICADO POR HUMANO]" in entry and target["step_id"] in entry for entry in body["audit_logs"])
        # El Registry valida parámetros: el paso modificado con parámetro no permitido queda en errors
        assert any(target["step_id"] in err for err in body["errors"])

    def test_paso_inyectado_con_operacion_no_registrada_no_ejecuta(self):
        _, plan = self._upload_and_propose()
        steps = plan["steps"] + [
            {
                "step_id": "step-maligno",
                "operation": "drop_database",
                "column": None,
                "parameters": {},
                "reason": "inyección",
                "status": "approved",
            }
        ]
        res = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": steps})
        assert res.status_code == 200
        body = res.json()
        assert any("[AÑADIDO POR HUMANO]" in entry and "step-maligno" in entry for entry in body["audit_logs"])
        assert any("step-maligno" in err for err in body["errors"])
        assert body["status"] == "completed_with_errors"

    def test_step_id_duplicado_devuelve_400(self):
        _, plan = self._upload_and_propose()
        steps = plan["steps"] + [dict(plan["steps"][0])]
        res = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": steps})
        assert res.status_code == 400
        assert res.json()["code"] == "DUPLICATE_STEP"
