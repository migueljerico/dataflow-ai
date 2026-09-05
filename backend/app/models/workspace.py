from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.models.dataset import DatasetMetadata


class TableRoleEnum(str, Enum):
    FACT = "fact"
    DIMENSION = "dimension"
    BRIDGE = "bridge"
    UNKNOWN = "unknown"


class RelationshipIntegrityAudit(BaseModel):
    from_table: str = Field(..., description="Tabla origen (lado muchos, clave foránea)")
    from_column: str = Field(..., description="Columna FK en tabla origen")
    to_table: str = Field(..., description="Tabla destino (lado uno, clave primaria)")
    to_column: str = Field(..., description="Columna PK en tabla destino")
    cardinality: str = Field(default="*:1", description="Cardinalidad de la relación (*:1)")
    total_fk_rows: int = Field(default=0, description="Total de filas con FK en la tabla origen")
    matching_fk_rows: int = Field(default=0, description="Filas con FK que coinciden con una PK existente")
    orphan_fk_rows: int = Field(default=0, description="Filas huérfanas (FK sin PK correspondiente)")
    match_percentage: float = Field(default=100.0, description="Porcentaje de coincidencia de integridad referencial")
    orphan_samples: List[Any] = Field(default_factory=list, description="Ejemplos de valores FK huérfanos")
    is_referential_clean: bool = Field(default=True, description="True si la integridad es 100% limpia")


class StarSchemaTableNode(BaseModel):
    table_id: str = Field(..., description="ID del dataset")
    table_name: str = Field(..., description="Nombre amigable de la tabla")
    role: TableRoleEnum = Field(..., description="Rol semántico (fact o dimension)")
    row_count: int = Field(default=0)
    column_count: int = Field(default=0)
    primary_keys: List[str] = Field(default_factory=list, description="Columnas identificadas como PK")
    foreign_keys: List[str] = Field(default_factory=list, description="Columnas identificadas como FK")
    attributes: List[str] = Field(default_factory=list, description="Atributos descriptivos")
    measures: List[str] = Field(default_factory=list, description="Medidas cuantitativas")


class MultiTableStarSchema(BaseModel):
    model_id: str = Field(..., description="ID único del modelo semántico")
    model_name: str = Field(default="StarSchema_Model", description="Nombre del modelo")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fact_table: StarSchemaTableNode = Field(..., description="Tabla de hechos central")
    dimension_tables: List[StarSchemaTableNode] = Field(
        default_factory=list, description="Tablas de dimensión conectadas"
    )
    relationships: List[RelationshipIntegrityAudit] = Field(default_factory=list, description="Relaciones validadas")
    suggested_dax_measures: Dict[str, str] = Field(
        default_factory=dict, description="Medidas DAX generadas para Power BI"
    )
    tmdl_definition: str = Field(default="", description="Definición TMDL completa del modelo semántico")
    referential_integrity_score: float = Field(default=100.0, description="Puntuación global de integridad del modelo")


class MultiFileUploadResponse(BaseModel):
    uploaded_count: int
    datasets: List[DatasetMetadata]
