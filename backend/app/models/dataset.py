from enum import Enum
from datetime import datetime, timezone
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Fecha de carga")
    status: ProcessingStateEnum = Field(default=ProcessingStateEnum.UPLOADED, description="Estado actual del pipeline")
    warnings: List[str] = Field(default_factory=list, description="Advertencias durante la validación")

class ErrorResponse(BaseModel):
    error: bool = True
    code: str
    message: str
    details: Dict[str, Any] = {}

class DatasetFromUrlRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL pública directa al archivo CSV o XLSX para importar",
        examples=["https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv"]
    )

class OpenDatasetItem(BaseModel):
    id: str = Field(..., description="ID del dataset en el portal Open Data")
    title: str = Field(..., description="Título legible del dataset")
    description: str = Field(..., description="Descripción o resumen del contenido")
    organization: str = Field(default="Open Data Portal", description="Organismo o entidad emisora")
    resource_url: str = Field(..., description="URL directa de descarga del archivo CSV/XLSX")
    format: str = Field(default="CSV", description="Formato del recurso (CSV, XLSX)")
    size_bytes: Optional[int] = Field(default=None, description="Tamaño del archivo en bytes si está disponible")
    tags: List[str] = Field(default_factory=list, description="Etiquetas temáticas (ej. Economía, Transporte)")

class OpenDataSearchResponse(BaseModel):
    total: int
    results: List[OpenDatasetItem]
    source: str = Field(default="CKAN Public Portal", description="Fuente de los metadatos")


