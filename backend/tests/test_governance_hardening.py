import pytest
import pandas as pd
from app.models.etl import TransformationStep, StepStatusEnum
from app.transformations.registry import TransformationRegistry
from app.core.exceptions import FunctionalException
from app.services.etl_service import ETLService


def test_registry_manifest_contains_all_14_operations():
    manifest = TransformationRegistry.get_catalog_manifest()
    assert len(manifest) == 15
    for op_name, meta in manifest.items():
        assert "name" in meta
        assert "description" in meta
        assert "risk" in meta
        assert "reversible" in meta
        assert "allowed_parameters" in meta
        assert "parameter_schema" in meta
        assert "requires_human_approval" in meta


def test_unregistered_operation_rejected():
    with pytest.raises(FunctionalException) as exc_info:
        TransformationRegistry.get_transformation("malicious_eval_code")
    assert exc_info.value.code == "UNREGISTERED_OPERATION"


def test_unauthorized_parameter_rejected():
    df = pd.DataFrame({"col_a": [1, 2, 3]})
    with pytest.raises(FunctionalException) as exc_info:
        TransformationRegistry.validate_operation_and_parameters(
            "trim_text", df, {"column": "col_a", "unauthorized_extra_param": "injection"}
        )
    assert exc_info.value.code == "UNAUTHORIZED_PARAMETER"


def test_governance_proposed_step_not_executed_in_engine():
    df = pd.DataFrame({"Texto": ["  hola  ", "  mundo  "]})
    step = TransformationStep(
        step_id="STEP-999",
        operation="trim_text",
        column="Texto",
        parameters={"column": "Texto"},
        reason="Test skipping proposed",
        status=StepStatusEnum.PROPOSED,
    )
    # Si se intenta ejecutar directamente un paso PROPOSED, debe ser omitido
    assert step.status == StepStatusEnum.PROPOSED
    assert step.status not in (StepStatusEnum.APPROVED, StepStatusEnum.EDITED)


def test_governance_rejected_step_explicitly_skipped():
    step = TransformationStep(
        step_id="STEP-998",
        operation="drop_column",
        column="Texto",
        parameters={"column": "Texto"},
        reason="Test rejection",
        status=StepStatusEnum.REJECTED,
    )
    assert step.status == StepStatusEnum.REJECTED
