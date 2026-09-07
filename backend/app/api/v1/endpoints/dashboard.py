"""
Endpoints de Dashboard Intelligence / Dashboard Preview.

Pipeline: esquema estrella → análisis semántico → planificador → motor de
visuales → validador WCAG → sistema de diseño → Blueprint → renderer (frontend).
La validación del Blueprint es determinista; el usuario puede editar propuestas
y revalidarlas sin que la IA sobrescriba sus decisiones.
"""

from app.core.exceptions import FunctionalException
from app.models.dashboard import (
    DashboardAnalyzeRequest,
    DashboardBlueprint,
    DashboardStats,
    DashboardValidateRequest,
    DashboardValidation,
)
from app.services.dashboard_service import DashboardService, get_dashboard_stats
from fastapi import APIRouter, status

router = APIRouter()


@router.post("/analyze", response_model=DashboardBlueprint, status_code=status.HTTP_200_OK)
async def analyze_dashboard(payload: DashboardAnalyzeRequest):
    """
    Analiza el esquema estrella (inferido o existente) y genera el Blueprint
    completo del dashboard: tipo recomendado, páginas, KPIs, visuales con
    justificación, filtros, paleta WCAG validada, medidas DAX, guía Power BI y
    previsualización con datos reales.
    """
    try:
        return DashboardService.analyze(payload.dataset_ids)
    except FunctionalException:
        raise
    except Exception as e:
        raise FunctionalException(
            message=f"Error al generar el Blueprint de dashboard: {str(e)}",
            code="DASHBOARD_ANALYZE_FAILED",
            status_code=400,
        ) from e


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_observability_stats() -> DashboardStats:
    """
    Métricas operativas del módulo: generaciones, fallos, validaciones,
    visuales recomendados y paletas rechazadas por WCAG.
    """
    return get_dashboard_stats()


@router.get("/{blueprint_id}", response_model=DashboardBlueprint)
async def get_dashboard_blueprint(blueprint_id: str):
    """Recupera un Blueprint previamente generado (caché en memoria)."""
    blueprint = DashboardService.get(blueprint_id)
    if not blueprint:
        raise FunctionalException(
            message="Blueprint de dashboard no encontrado o expirado.",
            code="BLUEPRINT_NOT_FOUND",
            status_code=404,
        )
    return blueprint


@router.post("/validate", response_model=DashboardValidation)
async def validate_dashboard_blueprint(payload: DashboardValidateRequest):
    """
    Valida un Blueprint (posiblemente editado por el usuario) contra el modelo
    estrella real: existencia de campos, compatibilidad de visuales, filtros,
    layout, reglas de circulares, WCAG y ausencia de referencias ficticias.
    """
    try:
        return DashboardService.validate_blueprint(payload.dataset_ids, payload.blueprint)
    except FunctionalException:
        raise
    except Exception as e:
        raise FunctionalException(
            message=f"Error al validar el Blueprint: {str(e)}",
            code="DASHBOARD_VALIDATE_FAILED",
            status_code=400,
        ) from e
