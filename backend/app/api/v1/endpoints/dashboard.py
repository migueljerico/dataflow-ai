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


@router.put("/{blueprint_id}", response_model=DashboardBlueprint, status_code=status.HTTP_200_OK)
async def update_dashboard_blueprint(blueprint_id: str, payload: DashboardBlueprint):
    """
    Guarda la edición HITL del usuario sobre un Blueprint existente (Paso 5).

    Gobernanza: la IA propone, el usuario decide, Python ejecuta. El endpoint
    aplica exactamente los cambios enviados, recalcula WCAG sobre la paleta
    activa, revalida de forma determinista y persiste el resultado en el
    StorageBackend activo (local/tmpfs o GCS/S3 según STORAGE_BACKEND).
    """
    if payload.blueprint_id != blueprint_id:
        raise FunctionalException(
            message="El ID del Blueprint del cuerpo no coincide con la ruta.",
            code="BLUEPRINT_ID_MISMATCH",
            status_code=400,
        )
    if DashboardService.get(blueprint_id) is None:
        raise FunctionalException(
            message="Blueprint de dashboard no encontrado o expirado.",
            code="BLUEPRINT_NOT_FOUND",
            status_code=404,
        )
    if not payload.dataset_ids:
        raise FunctionalException(
            message="El Blueprint debe conservar al menos un dataset para poder revalidarse.",
            code="BLUEPRINT_DATASETS_MISSING",
            status_code=400,
        )
    try:
        return DashboardService.save_edited(payload)
    except FunctionalException:
        raise
    except Exception as e:
        raise FunctionalException(
            message=f"Error al guardar el Blueprint editado: {str(e)}",
            code="DASHBOARD_UPDATE_FAILED",
            status_code=400,
        ) from e
