from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FileTypeEnum(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"

class ProcessingStateEnum(str, Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    PROFILED = "profiled"
    QUALITY_ANALYZED = "quality_analyzed"
    PLAN_PROPOSED = "plan_proposed"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    
    # Error states
    VALIDATION_FAILED = "validation_failed"
    PROFILING_FAILED = "profiling_failed"
    PLAN_INVALID = "plan_invalid"
    EXECUTION_FAILED = "execution_failed"

class DatasetMetadata(BaseModel):
    dataset_id: str = Field(..., description="Identificador único del dataset")
    filename: str = Field(..., description="Nombre original del archivo")
    file_type: FileTypeEnum = Field(..., description="Tipo de archivo (csv o xlsx)")
    size_bytes: int = Field(..., description="Tamaño del archivo en bytes")
    row_count: int = Field(..., description="Número total de filas detectadas")
    column_count: int = Field(..., description="Número total de columnas detectadas")
    columns: List[str] = Field(default_factory=list, description="Lista de nombres de columnas")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de carga")
    status: ProcessingStateEnum = Field(default=ProcessingStateEnum.UPLOADED, description="Estado actual del pipeline")
    warnings: List[str] = Field(default_factory=list, description="Advertencias durante la validación")

class ErrorResponse(BaseModel):
    error: bool = True
    code: str
    message: str
    details: Dict[str, Any] = {}
