from typing import List, Optional

from app.models.etl import ExecutionResult, TransformationPlan, TransformationStep
from app.services.ai_service import AIService
from app.services.etl_service import ETLService
from fastapi import APIRouter, Header, status
from pydantic import BaseModel

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
    req: ProposeAIPlanRequest, x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key")
):
    """
    Generar un plan de transformaciones asistido por la IA Copilot (Gemini / Mock).
    Aplica guardrails para garantizar que solo se sugieran operaciones registradas.
    Soporta BYOK (Bring Your Own Key) tanto por Header como por Request Body.
    """
    effective_key = req.api_key or x_gemini_api_key
    return await AIService.propose_ai_plan(
        dataset_id=req.dataset_id, provider_name=req.provider or "mock", api_key=effective_key
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

    Gobernanza reforzada (v1.16.0): el servidor contrasta los pasos recibidos
    contra la copia canónica del plan propuesto (diff controlado por step_id):
    - Contenido idéntico → se ejecuta la copia canónica del servidor como APPROVED.
    - Contenido divergente → EDITED con registro auditable [MODIFICADO POR HUMANO].
    - Pasos ajenos al plan → [AÑADIDO POR HUMANO] bajo validación del Registry.
    - El orden de ejecución es siempre el orden canónico del plan.

    Si el plan no existe (p. ej. el backend se reinició y se perdió la sesión),
    se devuelve 404 en lugar de ejecutar contra un dataset arbitrario: nunca
    se transforma un archivo sin trazabilidad completa de su plan asociado.
    """
    plan = ETLService.get_plan(plan_id)

    reviewed_steps, governance_notes = ETLService.reconcile_reviewed_steps(plan, req.steps)
    return ETLService.execute_plan(plan.dataset_id, plan_id, reviewed_steps, governance_notes=governance_notes)
