from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QualityDimensionEnum(str, Enum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    INTEGRITY = "integrity"


class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityIssue(BaseModel):
    issue_id: str = Field(..., description="ID único de la anomalía de calidad")
    dimension: QualityDimensionEnum = Field(..., description="Dimensión de calidad afectada")
    severity: SeverityEnum = Field(..., description="Nivel de severidad")
    column: Optional[str] = Field(None, description="Nombre de la columna afectada")
    description: str = Field(..., description="Explicación clara del problema")
    affected_rows: int = Field(..., description="Número de filas afectadas")
    affected_percentage: float = Field(..., description="Porcentaje de filas afectadas")
    evidence_sample: List[Any] = Field(default_factory=list, description="Muestra de valores con error")
    suggested_action: str = Field(..., description="Transformación o acción sugerida")


class DimensionBreakdown(BaseModel):
    score: float = Field(..., description="Puntuación de 0 a 100")
    weight: float = Field(..., description="Ponderación en la fórmula global")
    issues_count: int = Field(..., description="Cantidad de problemas detectados en la dimensión")
    summary: str = Field(..., description="Resumen explícito de la dimensión")


class QualityScore(BaseModel):
    overall_score: float = Field(..., description="Quality Score global (0 a 100)")
    completeness: DimensionBreakdown
    validity: DimensionBreakdown
    consistency: DimensionBreakdown
    uniqueness: DimensionBreakdown
    integrity: DimensionBreakdown
    explanation: str = Field(..., description="Explicación detallada de la puntuación obtenida")


class QualityReport(BaseModel):
    dataset_id: str = Field(..., description="ID del dataset")
    quality_score: QualityScore = Field(..., description="Puntuación de calidad explicable")
    issues: List[QualityIssue] = Field(default_factory=list, description="Lista de problemas detectados")
    issues_count: int = Field(..., description="Total de problemas detectados")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Fecha de análisis")
