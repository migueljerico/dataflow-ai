import io
import zipfile
from pathlib import Path
from typing import List, Optional

from app.core.exceptions import FunctionalException
from app.core.storage import get_storage
from app.models.etl import ExecutionResult
from app.models.quality import ExecutionSummaryItem, QualityComparisonReport
from app.services.etl_service import ETLService
from app.services.quality_service import QualityService
from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/batch/download-zip")
async def download_batch_clean_zip(
    run_ids: str = Query(..., description="IDs de ejecuciones separados por coma"),
):
    """
    Descargar todos los archivos limpios (CSV, Parquet y Scripts reproducible)
    de un lote de ejecuciones en un único paquete ZIP.
    """
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    if not ids:
        raise FunctionalException(
            message="Debe proporcionar al menos un ID de ejecución para generar el archivo ZIP.",
            code="EMPTY_RUN_IDS",
            status_code=400,
        )

    storage = get_storage()
    buf = io.BytesIO()
    files_added = 0

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rid in ids:
            try:
                run_res = ETLService.get_run_result(rid)
            except Exception:
                continue

            # 1. CSV
            clean_fn = run_res.clean_filename
            csv_candidates = [f"{rid}_{clean_fn}", clean_fn]
            for c_key in csv_candidates:
                if storage.exists(c_key):
                    csv_path = storage.get_path(c_key)
                    if csv_path.exists():
                        zf.write(csv_path, arcname=f"csv/{clean_fn}")
                        files_added += 1
                    break

            # 2. Parquet
            parquet_name = run_res.parquet_filename or f"clean_{run_res.dataset_id}.parquet"
            p_candidates = [f"{rid}_{parquet_name}", parquet_name]
            for p_key in p_candidates:
                if storage.exists(p_key):
                    p_path = storage.get_path(p_key)
                    if p_path.exists():
                        zf.write(p_path, arcname=f"parquet/{parquet_name}")
                        files_added += 1
                    break

            # 3. Script Python
            s_candidates = [
                f"pipeline_{rid}.py",
                f"script_{rid}.py",
                f"script_{run_res.dataset_id}.py",
            ]
            for s_key in s_candidates:
                if storage.exists(s_key):
                    s_path = storage.get_path(s_key)
                    if s_path.exists():
                        clean_stem = Path(clean_fn).stem
                        script_name = f"pipeline_{clean_stem}.py"
                        zf.write(s_path, arcname=f"scripts/{script_name}")
                        files_added += 1
                    break

    if files_added == 0:
        raise FunctionalException(
            message="No se encontraron archivos limpios para las ejecuciones solicitadas.",
            code="NO_CLEAN_FILES",
            status_code=404,
        )

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="datasets_limpios_lote.zip"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/", response_model=List[ExecutionSummaryItem])
async def list_runs_history(
    dataset_id: Optional[str] = Query(None, description="Filtrar historial por dataset específico"),
):
    """
    Listar el historial de ejecuciones ETL con estadísticas de calidad y métricas comparativas.
    """
    return ETLService.list_runs_history(dataset_id=dataset_id)


@router.get("/compare", response_model=QualityComparisonReport)
async def compare_two_runs(
    run_a: str = Query(..., description="ID de la primera ejecución (o versión base)"),
    run_b: str = Query(..., description="ID de la segunda ejecución (o versión comparada)"),
):
    """
    Comparar métricas de calidad dimensionales y globales entre dos ejecuciones o versiones de datasets.
    """
    comp_a = ETLService.get_quality_comparison(run_a)
    comp_b = ETLService.get_quality_comparison(run_b)

    delta = round(comp_b.overall_score_after - comp_a.overall_score_after, 2)
    return QualityComparisonReport(
        run_id=f"{run_a}_vs_{run_b}",
        dataset_id=f"{comp_a.dataset_id}->{comp_b.dataset_id}",
        overall_score_before=comp_a.overall_score_after,
        overall_score_after=comp_b.overall_score_after,
        delta_score=delta,
        dimensions=comp_b.dimensions,
        issues_count_before=comp_a.issues_count_after,
        issues_count_after=comp_b.issues_count_after,
        issues_resolved_count=max(0, comp_a.issues_count_after - comp_b.issues_count_after),
        explanation=f"Comparativa entre ejecución {run_a} ({comp_a.overall_score_after} pts) y ejecución {run_b} ({comp_b.overall_score_after} pts).",
        generated_at=comp_b.generated_at,
    )


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
    score_before = quality_before.quality_score.overall_score

    score_after = score_before
    score_delta = 0.0
    comparison_available = False
    try:
        comp = ETLService.get_quality_comparison(run_id)
        score_after = comp.overall_score_after
        score_delta = comp.delta_score
        comparison_available = True
    except Exception:
        pass

    return {
        "run_id": run_id,
        "dataset_id": result.dataset_id,
        "rows_before": result.rows_before,
        "rows_after": result.rows_after,
        "columns_before": result.columns_before,
        "columns_after": result.columns_after,
        "score_before": score_before,
        "score_after": score_after,
        "score_delta": score_delta,
        "comparison_available": comparison_available,
        "applied_steps": result.applied_steps_count,
        "execution_time_seconds": round(
            (result.finished_at - result.started_at).total_seconds(), 3
        ),
    }


@router.get("/{run_id}/quality-comparison", response_model=QualityComparisonReport)
async def get_run_quality_comparison(run_id: str):
    """
    Obtener el reporte detallado de comparación de calidad por dimensiones (Antes vs Después).
    """
    return ETLService.get_quality_comparison(run_id)


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
            message="El archivo limpio no está disponible para descarga.",
            code="FILE_NOT_FOUND",
            status_code=404,
        )

    return FileResponse(
        path=target_file, filename=result.clean_filename, media_type="application/octet-stream"
    )


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
            message="El script de Python no está disponible.",
            code="SCRIPT_NOT_FOUND",
            status_code=404,
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

    return FileResponse(
        path=target_file, filename=parquet_name, media_type="application/vnd.apache.parquet"
    )
