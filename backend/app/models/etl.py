from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Datetime UTC consciente de zona (datetime.utcnow está deprecado)."""
    return datetime.now(timezone.utc)


class StepStatusEnum(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class TransformationStep(BaseModel):
    step_id: str = Field(..., description="ID único del paso")
    operation: str = Field(..., description="Nombre de la operación del catálogo")
    column: Optional[str] = Field(None, description="Columna objetivo")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros de la transformación")
    reason: str = Field(..., description="Motivo funcional de la sugerencia")
    confidence: float = Field(default=0.9, description="Nivel de confianza de la regla o IA (0.0 a 1.0)")
    risk: str = Field(default="low", description="Riesgo de la operación (low, medium, high)")
    affected_rows_estimate: int = Field(default=0, description="Estimación de filas afectadas")
    status: StepStatusEnum = Field(default=StepStatusEnum.PROPOSED, description="Estado de revisión humana")


class TransformationPlan(BaseModel):
    plan_id: str = Field(..., description="ID del plan")
    dataset_id: str = Field(..., description="ID del dataset asociado")
    summary: str = Field(..., description="Resumen descriptivo del plan")
    steps: List[TransformationStep] = Field(default_factory=list, description="Lista de pasos ordenados")
    source: str = Field(default="rules_engine", description="Origen del plan: rules_engine o ai_assistant")
    created_at: datetime = Field(default_factory=utc_now, description="Fecha de creación")
    warnings: List[str] = Field(
        default_factory=list, description="Advertencias del plan (p. ej. operaciones IA descartadas por guardrails)"
    )


class ExecutionResult(BaseModel):
    run_id: str = Field(..., description="ID de la ejecución")
    dataset_id: str = Field(..., description="ID del dataset procesado")
    plan_id: str = Field(..., description="ID del plan ejecutado")
    status: str = Field(..., description="Estado final (completed o execution_failed)")
    started_at: datetime
    finished_at: datetime
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    applied_steps_count: int
    input_hash_md5: str
    output_hash_md5: str
    clean_filename: str
    download_url: str
    script_url: str
    parquet_filename: Optional[str] = Field(
        None, description="Nombre del archivo limpio serializado en Apache Parquet columnar"
    )
    parquet_url: Optional[str] = Field(
        None, description="URL directa de descarga del dataset limpio en formato Apache Parquet"
    )
    audit_logs: List[str] = Field(
        default_factory=list, description="Log detallado de validación y trazabilidad de cambios por paso"
    )
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
