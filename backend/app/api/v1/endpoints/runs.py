from app.core.exceptions import FunctionalException
from app.core.storage import get_storage
from app.models.etl import ExecutionResult
from app.services.etl_service import ETLService
from app.services.quality_service import QualityService
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/{run_id}", response_model=ExecutionResult)
async def get_run_result(run_id: str):
    """
    Obtener el resumen de la ejecución del plan ETL.
    """
    return ETLService.get_run_result(run_id)


@router.get("/{run_id}/report")
async def get_run_quality_report(run_id: str):
    """
    Obtener el informe comparativo de calidad Antes vs Después.
    """
    result = ETLService.get_run_result(run_id)
    quality_before = QualityService.get_quality_report(result.dataset_id)

    return {
        "run_id": run_id,
        "dataset_id": result.dataset_id,
        "rows_before": result.rows_before,
        "rows_after": result.rows_after,
        "columns_before": result.columns_before,
        "columns_after": result.columns_after,
        "score_before": quality_before.quality_score.overall_score,
        "applied_steps": result.applied_steps_count,
        "execution_time_seconds": round((result.finished_at - result.started_at).total_seconds(), 3),
    }


@router.get("/{run_id}/download")
async def download_clean_dataset(run_id: str):
    """
    Descargar el dataset limpio resultante de la ejecución ETL.
    """
    result = ETLService.get_run_result(run_id)
    storage = get_storage()
    candidates = [
        f"{run_id}_{result.clean_filename}",
        result.clean_filename,
    ]
    target_file = None
    for key in candidates:
        if storage.exists(key):
            target_file = storage.get_path(key)
            break

    if not target_file or not target_file.exists():
        raise FunctionalException(
            message="El archivo limpio no está disponible para descarga.", code="FILE_NOT_FOUND", status_code=404
        )

    return FileResponse(path=target_file, filename=result.clean_filename, media_type="application/octet-stream")


@router.get("/{run_id}/script")
@router.get("/{run_id}/download-script")
async def download_reproducible_script(run_id: str):
    """
    Descargar el script de Python standalone reproducible (.py).
    """
    result = ETLService.get_run_result(run_id)
    storage = get_storage()
    candidates = [
        f"pipeline_{run_id}.py",
        f"script_{run_id}.py",
        f"script_{result.dataset_id}.py",
    ]
    target_file = None
    for key in candidates:
        if storage.exists(key):
            target_file = storage.get_path(key)
            break

    if not target_file or not target_file.exists():
        raise FunctionalException(
            message="El script de Python no está disponible.", code="SCRIPT_NOT_FOUND", status_code=404
        )

    return FileResponse(path=target_file, filename=f"pipeline_{run_id}.py", media_type="text/plain")


@router.get("/{run_id}/parquet")
@router.get("/{run_id}/download-parquet")
@router.get("/{run_id}/download/parquet")
async def download_parquet_dataset(run_id: str):
    """
    Descargar el dataset limpio serializado en formato nativo Apache Parquet columnar
    para analítica de alto rendimiento (Power BI, DuckDB, Spark, etc.).
    """
    result = ETLService.get_run_result(run_id)
    storage = get_storage()
    parquet_name = result.parquet_filename or f"clean_{result.dataset_id}.parquet"
    candidates = [
        f"{run_id}_{parquet_name}",
        parquet_name,
    ]
    target_file = None
    for key in candidates:
        if storage.exists(key):
            target_file = storage.get_path(key)
            break

    if not target_file or not target_file.exists():
        raise FunctionalException(
            message="El archivo Apache Parquet no está disponible para descarga.",
            code="PARQUET_NOT_FOUND",
            status_code=404,
        )

    return FileResponse(path=target_file, filename=parquet_name, media_type="application/vnd.apache.parquet")
