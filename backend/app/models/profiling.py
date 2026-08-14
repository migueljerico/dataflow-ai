from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ColumnTypeEnum(str, Enum):
    NUMERIC = "numeric"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"

class SemanticHintEnum(str, Enum):
    ID = "id"
    EMAIL = "email"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    PHONE = "phone"
    LOCATION = "location"
    NAME = "name"
    UNKNOWN = "unknown"

class ColumnProfile(BaseModel):
    column_name: str = Field(..., description="Nombre de la columna")
    inferred_type: ColumnTypeEnum = Field(..., description="Tipo inferido por el profiling")
    semantic_hint: SemanticHintEnum = Field(default=SemanticHintEnum.UNKNOWN, description="Sugerencia semántica")
    null_count: int = Field(..., description="Cantidad de valores nulos o vacíos")
    null_percentage: float = Field(..., description="Porcentaje de nulos (0 a 100)")
    unique_count: int = Field(..., description="Cantidad de valores únicos distintos")
    sample_values: List[Any] = Field(default_factory=list, description="Muestra de valores representativos")
    
    # Estadísticas opcionales según el tipo
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    
    # Advertencias específicas de la columna
    warnings: List[str] = Field(default_factory=list, description="Advertencias detectadas en la columna")

class ProfilingReport(BaseModel):
    dataset_id: str = Field(..., description="ID del dataset analizado")
    row_count: int = Field(..., description="Total de filas")
    column_count: int = Field(..., description="Total de columnas")
    duplicates_count: int = Field(..., description="Filas duplicadas exactas detectadas")
    duplicates_percentage: float = Field(..., description="Porcentaje de filas duplicadas")
    memory_estimate_bytes: int = Field(..., description="Estimación de uso de memoria RAM")
    columns: List[ColumnProfile] = Field(default_factory=list, description="Perfil detallado de cada columna")
    global_warnings: List[str] = Field(default_factory=list, description="Advertencias globales del dataset")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de generación")
