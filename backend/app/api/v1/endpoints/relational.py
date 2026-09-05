from typing import Dict, List

from app.models.workspace import MultiTableStarSchema
from app.services.relational_service import RelationalService
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

router = APIRouter()

# Caché en memoria para modelos generados
RELATIONAL_MODELS_CACHE: Dict[str, MultiTableStarSchema] = {}


class StarSchemaRequest(BaseModel):
    dataset_ids: List[str] = Field(..., min_length=1, description="Lista de IDs de datasets a relacionar en el modelo")


@router.post("/star-schema", response_model=MultiTableStarSchema, status_code=status.HTTP_200_OK)
async def generate_star_schema(payload: StarSchemaRequest):
    """
    Genera un Esquema de Estrella multi-tabla automático a partir de los datasets seleccionados.
    Detecta claves primarias, foráneas, audita integridad referencial y genera el modelo TMDL / DAX para Power BI.
    """
    try:
        schema = RelationalService.infer_star_schema(payload.dataset_ids)
        RELATIONAL_MODELS_CACHE[schema.model_id] = schema
        return schema
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al inferir el esquema estrella: {str(e)}"
        ) from e


@router.get("/models/{model_id}/tmdl")
async def download_model_tmdl(model_id: str):
    """
    Descarga la definición TMDL del modelo estrella multi-tabla para Power BI Desktop.
    """
    schema = RELATIONAL_MODELS_CACHE.get(model_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Modelo semántico no encontrado.")

    filename = f"{schema.model_name}.tmdl"
    return Response(
        content=schema.tmdl_definition,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
