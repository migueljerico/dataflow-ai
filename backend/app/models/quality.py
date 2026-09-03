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


class DimensionComparison(BaseModel):
    dimension: QualityDimensionEnum = Field(..., description="Dimensión evaluada")
    score_before: float = Field(..., description="Puntuación antes de la transformación")
    score_after: float = Field(..., description="Puntuación después de la transformación")
    delta: float = Field(..., description="Variación absoluta de puntuación (+ o -)")
    issues_before: int = Field(..., description="Problemas detectados antes")
    issues_after: int = Field(..., description="Problemas restantes tras la transformación")
    summary: str = Field(..., description="Resumen explicativo del cambio en la dimensión")


class QualityComparisonReport(BaseModel):
    run_id: str = Field(..., description="ID de la ejecución")
    dataset_id: str = Field(..., description="ID del dataset original")
    overall_score_before: float = Field(..., description="Puntuación global antes")
    overall_score_after: float = Field(..., description="Puntuación global después")
    delta_score: float = Field(..., description="Incremento o variación en el score general")
    dimensions: List[DimensionComparison] = Field(default_factory=list, description="Comparativa por dimensión")
    issues_count_before: int = Field(..., description="Total de anomalías antes")
    issues_count_after: int = Field(..., description="Total de anomalías tras la transformación")
    issues_resolved_count: int = Field(..., description="Cantidad de anomalías subsanadas")
    explanation: str = Field(..., description="Resumen cualitativo de la mejora de calidad")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Fecha de cálculo")


class ExecutionSummaryItem(BaseModel):
    run_id: str = Field(..., description="ID único de la ejecución")
    dataset_id: str = Field(..., description="ID del dataset fuente")
    filename: str = Field(..., description="Nombre del archivo original")
    clean_filename: str = Field(..., description="Nombre del archivo limpio generado")
    status: str = Field(..., description="Estado de la ejecución")
    started_at: datetime = Field(..., description="Momento de inicio")
    finished_at: datetime = Field(..., description="Momento de finalización")
    execution_time_seconds: float = Field(..., description="Tiempo de ejecución en segundos")
    rows_before: int = Field(..., description="Filas iniciales")
    rows_after: int = Field(..., description="Filas resultantes")
    columns_before: int = Field(..., description="Columnas iniciales")
    columns_after: int = Field(..., description="Columnas finales")
    applied_steps_count: int = Field(..., description="Pasos de transformación aplicados")
    score_before: float = Field(..., description="Quality score original")
    score_after: float = Field(..., description="Quality score limpio")
    score_delta: float = Field(..., description="Variación del quality score")
    input_hash_md5: str = Field(..., description="MD5 del dataset crudo")
    output_hash_md5: str = Field(..., description="MD5 del dataset transformado")
    download_url: str = Field(..., description="URL de descarga CSV")
    parquet_url: Optional[str] = Field(None, description="URL de descarga Parquet")
    script_url: Optional[str] = Field(None, description="URL de descarga script Python")
