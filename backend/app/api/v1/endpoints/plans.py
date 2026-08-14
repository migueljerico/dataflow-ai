from typing import List, Optional
from fastapi import APIRouter, Header, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.exceptions import FunctionalException
from app.models.etl import TransformationPlan, TransformationStep, ExecutionResult
from app.services.etl_service import ETLService
from app.services.ai_service import AIService

router = APIRouter()

class ProposePlanRequest(BaseModel):
    dataset_id: str

class ProposeAIPlanRequest(BaseModel):
    dataset_id: str
    provider: Optional[str] = "mock"
    api_key: Optional[str] = None

class ApprovePlanRequest(BaseModel):
    steps: List[TransformationStep]

@router.post("/propose", response_model=TransformationPlan, status_code=status.HTTP_201_CREATED)
async def propose_plan(req: ProposePlanRequest):
    """
    Generar un plan de transformaciones sugerido a partir de reglas deterministas.
    """
    return ETLService.propose_plan_from_rules(req.dataset_id)

@router.post("/propose/ai", response_model=TransformationPlan, status_code=status.HTTP_201_CREATED)
async def propose_ai_plan(
    req: ProposeAIPlanRequest,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key")
):
    """
    Generar un plan de transformaciones asistido por la IA Copilot (Gemini / Mock).
    Aplica guardrails para garantizar que solo se sugieran operaciones registradas.
    Soporta BYOK (Bring Your Own Key) tanto por Header como por Request Body.
    """
    effective_key = req.api_key or x_gemini_api_key
    return await AIService.propose_ai_plan(
        dataset_id=req.dataset_id,
        provider_name=req.provider or "mock",
        api_key=effective_key
    )

@router.get("/{plan_id}", response_model=TransformationPlan)
async def get_plan(plan_id: str):
    """
    Obtener un plan de transformaciones por su ID.
    """
    return ETLService.get_plan(plan_id)

@router.post("/{plan_id}/approve", response_model=ExecutionResult)
async def approve_and_execute_plan(plan_id: str, req: ApprovePlanRequest):
    """
    Aprobar las transformaciones revisadas por el usuario y desencadenar
    la ejecución determinista del motor ETL en Python/pandas.
    """
    dataset_id = ""
    try:
        plan = ETLService.get_plan(plan_id)
        dataset_id = plan.dataset_id
    except Exception:
        pass

    if not dataset_id:
        uploaded_files = [f for f in settings.UPLOAD_DIR.glob("*_*") if not f.name.startswith("clean_") and not f.name.startswith("script_")]
        if uploaded_files:
            dataset_id = uploaded_files[0].name.split("_")[0]
        else:
            raise FunctionalException(message="No hay ningún dataset activo para ejecutar el plan. Por favor, vuelve a subir el archivo.", code="DATASET_NOT_FOUND")

    return ETLService.execute_plan(dataset_id, plan_id, req.steps)
