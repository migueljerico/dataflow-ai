import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

from app.core.exceptions import FunctionalException
from app.core.number_parsing import (
    get_numeric_parseable_ratio,
    is_missing_series,
    is_missing_value,
    to_numeric_series,
)
from app.core.semantics import is_id_or_code_column, is_percentage_or_score_column
from app.core.storage import get_storage
from app.models.dataset import FileTypeEnum, ProcessingStateEnum
from app.models.etl import ExecutionResult, StepStatusEnum, TransformationPlan, TransformationStep
from app.services.dataset_service import DatasetService
from app.services.quality_service import QualityService
from app.services.script_generator import ScriptGeneratorService
from app.transformations.registry import TransformationRegistry

PLANS_CACHE: Dict[str, TransformationPlan] = {}
RUNS_CACHE: Dict[str, ExecutionResult] = {}


def _count_modified_cells(series_orig: pd.Series, series_curr: pd.Series) -> int:
    """Conteo de celdas modificadas seguro ante missing values (NaN != NaN es True)."""
    a = series_orig.astype(str)
    b = series_curr.astype(str)
    both_missing = a.isna() & b.isna()
    return int(((a != b) & ~both_missing).sum())


def _is_percentage_or_score_column(col_name: str, raw_series: pd.Series, numeric_series: pd.Series = None) -> bool:
    """
    Determina si una columna es de tipo porcentaje o score acotado a [0, 100].
    Delega a app.core.semantics garantizando que columnas de texto libre nunca sean porcentajes.
    """
    return is_percentage_or_score_column(col_name, raw_series)


class ETLService:
    @staticmethod
    def propose_plan_from_rules(dataset_id: str) -> TransformationPlan:
        quality_report = QualityService.get_quality_report(dataset_id)
        df = DatasetService.load_dataframe(dataset_id)
        steps: List[TransformationStep] = []

        # 1. Sugerencias desde Quality Issues
        for issue in quality_report.issues:
            step_id = f"STEP-{len(steps)+1:03d}"
            col = issue.column
            dim = issue.dimension.value if hasattr(issue.dimension, "value") else str(issue.dimension)

            if dim == "uniqueness":
                if not any(s.operation == "remove_duplicates" for s in steps):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="remove_duplicates",
                            column=None,
                            parameters={},
                            reason="Eliminar filas duplicadas exactas para garantizar la unicidad del dataset.",
                            confidence=0.95,
                            risk="high",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )

            elif dim == "consistency":
                if (
                    "espacios" in issue.description.lower()
                    and col
                    and not any(s.column == col and s.operation == "trim_text" for s in steps)
                ):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="trim_text",
                            column=col,
                            parameters={"column": col},
                            reason=f"Limpiar espacios iniciales/finales y dobles espacios en '{col}'.",
                            confidence=0.98,
                            risk="low",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )
                elif (
                    ("mayúsculas" in issue.description.lower() or "formato" in issue.description.lower())
                    and col
                    and not any(s.column == col and s.operation == "normalize_case" for s in steps)
                ):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="normalize_case",
                            column=col,
                            parameters={"column": col, "mode": "title"},
                            reason=f"Normalizar formato de texto en '{col}' a Title Case (preservando siglas de negocio SA, SL, KPI, etc.).",
                            confidence=0.92,
                            risk="low",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )

            elif dim == "validity" and col:
                if ("fecha" in issue.description.lower() or "datetime" in issue.description.lower()) and not any(
                    s.column == col and s.operation == "convert_datetime" for s in steps
                ):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="convert_datetime",
                            column=col,
                            parameters={"column": col, "target_format": "%Y-%m-%d"},
                            reason=f"Estandarizar formato heterogéneo de fechas en '{col}' a ISO 8601 (YYYY-MM-DD).",
                            confidence=0.95,
                            risk="low",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )
                elif (
                    "símbolos" in issue.description.lower()
                    or "marcadores" in issue.description.lower()
                    or "cuantitativa" in issue.description.lower()
                ) and not any(s.column == col and s.operation == "convert_numeric" for s in steps):
                    loss_warning = None
                    if col and col in df.columns:
                        missing_mask = is_missing_series(df[col])
                        real_content = df[col][~missing_mask]
                        if len(real_content) > 0:
                            parsed_real = to_numeric_series(real_content)
                            lost_count = int(parsed_real.isna().sum())
                            if lost_count > 0:
                                loss_warning = (
                                    f"Atención: {lost_count} celda(s) contienen texto libre o caracteres no numéricos "
                                    f"que se descartarán irreversiblemente como NaN."
                                )
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="convert_numeric",
                            column=col,
                            parameters={"column": col},
                            reason=f"Limpiar símbolos y marcadores de ausencia (N/A, N/D, --, -) en '{col}' convirtiendo a numérico puro float64 para Power BI.",
                            confidence=0.95,
                            risk="medium",
                            affected_rows_estimate=issue.affected_rows,
                            data_loss_warning=loss_warning,
                        )
                    )

            elif dim == "integrity" and col:
                col_nums = to_numeric_series(df[col]).dropna() if col in df.columns else pd.Series()
                col_is_pct = _is_percentage_or_score_column(col, df[col], col_nums) if col in df.columns else False
                if col_is_pct and not any(s.column == col and s.operation == "clamp_range" for s in steps):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": 0.0, "max_value": 100.0},
                            reason=f"Acotar valores fuera de rango en '{col}' al intervalo de negocio [0.0, 100.0%].",
                            confidence=0.94,
                            risk="medium",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )
                elif ("negativos" in issue.description.lower() or "negativo" in issue.description.lower()) and not any(
                    s.column == col and s.operation == "clamp_range" for s in steps
                ):
                    min_v = 0.0 if col_is_pct else 0
                    max_v = 100.0 if col_is_pct else None
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": min_v, "max_value": max_v},
                            reason=(
                                f"Acotar valores fuera de rango en la columna porcentual '{col}' al intervalo de negocio [0.0, 100.0%]."
                                if col_is_pct
                                else f"Acotar {issue.affected_rows} valor(es) negativo(s) ilógico(s) en '{col}' estableciendo piso mínimo en 0."
                            ),
                            confidence=0.94,
                            risk="medium",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )
                elif (
                    "superiores" in issue.description.lower()
                    or "rango" in issue.description.lower()
                    or "porcentual" in issue.description.lower()
                ) and not any(s.column == col and s.operation == "clamp_range" for s in steps):
                    steps.append(
                        TransformationStep(
                            step_id=step_id,
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": 0.0, "max_value": 100.0},
                            reason=f"Acotar valores fuera de rango en '{col}' al intervalo de negocio [0.0, 100.0%].",
                            confidence=0.94,
                            risk="medium",
                            affected_rows_estimate=issue.affected_rows,
                        )
                    )

            elif (
                dim == "completeness"
                and col
                and not any(s.column == col and s.operation == "fill_missing" for s in steps)
            ):
                steps.append(
                    TransformationStep(
                        step_id=step_id,
                        operation="fill_missing",
                        column=col,
                        parameters={"column": col, "strategy": "constant", "value": "Desconocido"},
                        reason=f"Imputar nulos en '{col}' con valor constante por defecto.",
                        confidence=0.85,
                        risk="medium",
                        affected_rows_estimate=issue.affected_rows,
                    )
                )

        # 2. Heurística Semántica Universal de Respaldo sobre Columnas
        for col_name in df.columns:
            series_raw = df[col_name].dropna().astype(str)
            col_lower = col_name.lower()

            is_id = (
                col_lower.startswith("id")
                or col_lower.endswith("_id")
                or col_lower.startswith("cod")
                or col_lower.endswith("_cod")
                or "codigo" in col_lower
                or "code" in col_lower
                or "pedido" in col_lower
                or "cif" in col_lower
                or "dni" in col_lower
                or "nif" in col_lower
                or "sku" in col_lower
                or "ref" in col_lower
                or "referencia" in col_lower
            )
            is_quant_or_date = (
                pd.api.types.is_numeric_dtype(df[col_name])
                or pd.api.types.is_datetime64_any_dtype(df[col_name])
                or any(
                    k in col_lower
                    for k in [
                        "fecha",
                        "date",
                        "horas",
                        "dias",
                        "precio",
                        "salario",
                        "sueldo",
                        "monto",
                        "cantidad",
                        "unidades",
                        "llamadas",
                        "aht",
                        "segundos",
                        "minutos",
                        "stock",
                        "descuento",
                        "importe",
                    ]
                )
            )

            # Nombres / Entidades / Categorías en mayúsculas (excluyendo IDs y numéricas)
            if (
                not is_id
                and not is_quant_or_date
                and not any(s.column == col_name and s.operation == "normalize_case" for s in steps)
            ):
                if any(len(x.strip()) > 2 and x.strip().isupper() for x in series_raw):
                    steps.append(
                        TransformationStep(
                            step_id=f"STEP-{len(steps)+1:03d}",
                            operation="normalize_case",
                            column=col_name,
                            parameters={"column": col_name, "mode": "title"},
                            reason=f"Normalizar formato de texto en '{col_name}' a Title Case (preservando siglas como SA, SL, SLU).",
                            confidence=0.92,
                            risk="low",
                            affected_rows_estimate=len(df),
                        )
                    )

            # Espacios en blanco sobrantes
            if not any(s.column == col_name and s.operation == "trim_text" for s in steps):
                if any(x != x.strip() or "  " in x for x in series_raw):
                    steps.append(
                        TransformationStep(
                            step_id=f"STEP-{len(steps)+1:03d}",
                            operation="trim_text",
                            column=col_name,
                            parameters={"column": col_name},
                            reason=f"Limpiar espacios sobrantes en '{col_name}'.",
                            confidence=0.95,
                            risk="low",
                            affected_rows_estimate=len(df),
                        )
                    )

            # Marcadores N/D / N/A / -- o símbolos en series convertibles a numérico
            if not is_id and not any(s.column == col_name and s.operation == "convert_numeric" for s in steps):
                ratio, _, total_real = get_numeric_parseable_ratio(df[col_name])
                if total_real > 0 and ratio >= 0.8:
                    has_dirty = any(
                        is_missing_value(v)
                        or any(sym in v for sym in ["€", "$", "%", "usd", "eur"])
                        or bool(re.search(r"\d,\d", v))
                        for v in series_raw
                    )
                    if has_dirty:
                        loss_warning = None
                        if col_name in df.columns:
                            missing_mask = is_missing_series(df[col_name])
                            real_content = df[col_name][~missing_mask]
                            if len(real_content) > 0:
                                parsed_real = to_numeric_series(real_content)
                                lost_count = int(parsed_real.isna().sum())
                                if lost_count > 0:
                                    loss_warning = (
                                        f"Atención: {lost_count} celda(s) contienen texto libre o caracteres no numéricos "
                                        f"que se descartarán irreversiblemente como NaN."
                                    )
                        steps.append(
                            TransformationStep(
                                step_id=f"STEP-{len(steps)+1:03d}",
                                operation="convert_numeric",
                                column=col_name,
                                parameters={"column": col_name},
                                reason=f"Convertir '{col_name}' a numérico puro float64 asignando marcadores de ausencia (N/A, N/D, --, -) a nulos (NaN) para Power BI.",
                                confidence=0.95,
                                risk="medium",
                                affected_rows_estimate=len(df),
                                data_loss_warning=loss_warning,
                            )
                        )

            # Valores numéricos fuera de rango (excluyendo IDs)
            if not is_id:
                clean_nums = to_numeric_series(series_raw).dropna()
                if len(clean_nums) > 0:
                    is_pct = _is_percentage_or_score_column(col_name, df[col_name], clean_nums)

                    # Negativos
                    if (
                        not is_pct
                        and (clean_nums < 0).sum() > 0
                        and not any(s.column == col_name and s.operation == "clamp_range" for s in steps)
                    ):
                        neg_count = int((clean_nums < 0).sum())
                        steps.append(
                            TransformationStep(
                                step_id=f"STEP-{len(steps)+1:03d}",
                                operation="clamp_range",
                                column=col_name,
                                parameters={"column": col_name, "min_value": 0, "max_value": None},
                                reason=f"Acotar {neg_count} valor(es) negativo(s) ilógico(s) en '{col_name}' estableciendo piso mínimo en 0.",
                                confidence=0.94,
                                risk="medium",
                                affected_rows_estimate=neg_count,
                            )
                        )

                    # Porcentajes fuera de rango (<0 o >100)
                    if (
                        is_pct
                        and ((clean_nums > 100).sum() > 0 or (clean_nums < 0).sum() > 0)
                        and not any(s.column == col_name and s.operation == "clamp_range" for s in steps)
                    ):
                        out_count = int(((clean_nums > 100) | (clean_nums < 0)).sum())
                        steps.append(
                            TransformationStep(
                                step_id=f"STEP-{len(steps)+1:03d}",
                                operation="clamp_range",
                                column=col_name,
                                parameters={"column": col_name, "min_value": 0.0, "max_value": 100.0},
                                reason=f"Acotar {out_count} valor(es) fuera de rango en '{col_name}' al intervalo porcentual de negocio [0.0, 100.0%].",
                                confidence=0.94,
                                risk="medium",
                                affected_rows_estimate=out_count,
                            )
                        )

        plan_id = f"PLAN-{uuid.uuid4().hex[:8]}"
        plan = TransformationPlan(
            plan_id=plan_id,
            dataset_id=dataset_id,
            summary=f"Plan de transformaciones determinista sugerido por el Data Quality Engine ({len(steps)} pasos).",
            steps=steps,
            source="rules_engine",
            created_at=datetime.now(timezone.utc),
        )

        metadata = DatasetService.get_dataset_metadata(dataset_id)
        metadata.status = ProcessingStateEnum.PLAN_PROPOSED
        PLANS_CACHE[plan_id] = plan
        return plan

    @staticmethod
    def get_plan(plan_id: str) -> TransformationPlan:
        if plan_id not in PLANS_CACHE:
            raise FunctionalException(
                message=f"El plan de transformaciones '{plan_id}' no fue encontrado o ha caducado. Por favor, vuelve a generarlo antes de ejecutarlo.",
                code="PLAN_NOT_FOUND",
                status_code=404,
            )
        return PLANS_CACHE[plan_id]

    @staticmethod
    def execute_plan(dataset_id: str, plan_id: str, steps: List[TransformationStep]) -> ExecutionResult:
        started_at = datetime.now(timezone.utc)
        metadata = DatasetService.get_dataset_metadata(dataset_id)
        df_raw = DatasetService.load_dataframe(dataset_id)
        raw_filepath = DatasetService.get_saved_filepath(dataset_id)

        with open(raw_filepath, "rb") as f:
            input_md5 = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

        rows_before, cols_before = df_raw.shape
        df_current = df_raw.copy()
        applied_steps: List[TransformationStep] = []
        audit_logs: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Registro explícito de descarte de filas vacías si existieron
        empty_rows_purged = DatasetService.get_empty_rows_purged(dataset_id)
        if empty_rows_purged > 0:
            audit_logs.append(
                f"[VALIDACIÓN OK] Operación 'drop_empty_rows': Se detectaron y descartaron {empty_rows_purged} fila(s) completamente vacías o malformadas (,,,,,,,)."
            )

        for step in steps:
            # GOBERNANZA ESTRICTA: Solo se ejecutan pasos con estado APPROVED o EDITED
            if step.status == StepStatusEnum.REJECTED:
                audit_logs.append(
                    f"[OMITIDO] Paso {step.step_id} ({step.operation}): Rechazado explícitamente por el usuario."
                )
                continue

            if step.status == StepStatusEnum.PROPOSED:
                audit_logs.append(
                    f"[OMITIDO] Paso {step.step_id} ({step.operation}): Omitido por permanecer en estado propuesto sin aprobación humana."
                )
                continue

            if step.status not in (StepStatusEnum.APPROVED, StepStatusEnum.EDITED):
                audit_logs.append(
                    f"[OMITIDO] Paso {step.step_id} ({step.operation}): Estado no ejecutable ('{step.status}')."
                )
                continue

            try:
                # Validar operación registrada y conformidad de parámetros contra el schema
                transformation = TransformationRegistry.validate_operation_and_parameters(
                    step.operation, df_current, step.parameters
                )
                target_col = step.column or step.parameters.get("column")

                # Snapshot pre-transformación para cálculo real de modificaciones
                series_orig = df_current[target_col].copy() if target_col and target_col in df_current.columns else None
                rows_prior = len(df_current)

                # Ejecución determinista en pandas desempaquetando tupla
                res = transformation.apply(df_current, step.parameters)
                df_current = res[0] if isinstance(res, tuple) else res
                applied_steps.append(step)

                # Cálculo de auditoría con datos reales
                if step.operation == "remove_duplicates":
                    dropped = rows_prior - len(df_current)
                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación 'remove_duplicates': {dropped} fila(s) duplicada(s) eliminada(s) ({len(df_current)} registros únicos)."
                    )

                elif step.operation == "convert_datetime" and target_col:
                    nulls_after = df_current[target_col].isna().sum()
                    nulls_before = series_orig.isna().sum() if series_orig is not None else 0
                    invalid_dates = max(0, nulls_after - nulls_before)
                    converted = len(df_current) - nulls_after
                    if invalid_dates > 0:
                        audit_logs.append(
                            f"[VALIDACIÓN OK] Operación 'convert_datetime' en '{target_col}': {converted} fechas estandarizadas a ISO 8601 (%Y-%m-%d) sin inversión de día/mes. Se identificaron y descartaron {invalid_dates} fecha(s) con formato inválido irrecuperable (invalid_date)."
                        )
                    else:
                        audit_logs.append(
                            f"[VALIDACIÓN OK] Operación 'convert_datetime' en '{target_col}': {converted} fechas estandarizadas a ISO 8601 (%Y-%m-%d) con 0 pérdidas de datos y discriminación estricta de formatos."
                        )

                elif step.operation == "clamp_range" and target_col:
                    min_val = step.parameters.get("min_value")
                    max_val = step.parameters.get("max_value")
                    range_str = (
                        f"[{min_val if min_val is not None else '-inf'}, {max_val if max_val is not None else 'inf'}]"
                    )

                    if series_orig is not None:
                        orig_clean = to_numeric_series(series_orig)
                        curr_clean = pd.to_numeric(df_current[target_col], errors="coerce")
                        # Evitar bug IEEE 754 (NaN != NaN)
                        modified = int(((orig_clean != curr_clean) & ~(orig_clean.isna() & curr_clean.isna())).sum())
                    else:
                        modified = len(df_current)

                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación 'clamp_range' en '{target_col}': {modified} valor(es) acotados al rango de negocio {range_str}."
                    )

                elif step.operation == "convert_numeric" and target_col:
                    if series_orig is not None:
                        modified = _count_modified_cells(series_orig, df_current[target_col])
                    else:
                        modified = len(df_current)
                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación 'convert_numeric' en '{target_col}': {modified} celda(s) convertidas a float64 (símbolos, separadores europeos/americanos y marcadores N/D asignados a NaN)."
                    )

                elif step.operation == "normalize_case" and target_col:
                    if series_orig is not None:
                        modified = _count_modified_cells(series_orig, df_current[target_col])
                    else:
                        modified = len(df_current)
                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación 'normalize_case' en '{target_col}': {modified} registro(s) normalizados a formato homogéneo (preservando siglas de negocio)."
                    )

                elif step.operation == "trim_text" and target_col:
                    if series_orig is not None:
                        modified = _count_modified_cells(series_orig, df_current[target_col])
                    else:
                        modified = len(df_current)
                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación 'trim_text' en '{target_col}': {modified} celda(s) limpiadas de espacios sobrantes."
                    )

                else:
                    audit_logs.append(
                        f"[VALIDACIÓN OK] Operación '{step.operation}' aplicada en '{target_col or 'dataset'}'."
                    )

            except Exception as e:
                errors.append(f"Error al ejecutar paso {step.step_id} ({step.operation}): {str(e)}")

        # Preservar tipos de columnas ID antes de guardar para garantizar ceros a la izquierda
        for c in df_current.columns:
            if is_id_or_code_column(c, df_current[c]):
                df_current[c] = df_current[c].astype(str)

        # Guardar dataset limpio mediante StorageBackend
        run_id = f"RUN-{uuid.uuid4().hex[:8]}"
        clean_filename = f"clean_{metadata.filename}"
        clean_key = f"{run_id}_{clean_filename}"
        storage = get_storage()

        if metadata.file_type == FileTypeEnum.CSV:
            buf = io.BytesIO()
            df_current.to_csv(buf, index=False, encoding="utf-8")
            clean_bytes = buf.getvalue()
        else:
            buf = io.BytesIO()
            df_current.to_excel(buf, index=False)
            clean_bytes = buf.getvalue()

        storage.save_file(clean_key, clean_bytes)
        output_md5 = hashlib.md5(clean_bytes, usedforsecurity=False).hexdigest()

        # Generar y almacenar dataset limpio en formato nativo Apache Parquet (columnar de alto rendimiento)
        base_stem = Path(metadata.filename).stem
        parquet_filename = f"clean_{base_stem}.parquet"
        parquet_key = f"{run_id}_{parquet_filename}"
        parquet_buf = io.BytesIO()
        df_current.to_parquet(parquet_buf, index=False, engine="pyarrow")
        storage.save_file(parquet_key, parquet_buf.getvalue())

        # Generar y almacenar script reproducible
        script_content = ScriptGeneratorService.generate_script(
            source_filename=metadata.filename, file_type=metadata.file_type.value, steps=applied_steps, run_id=run_id
        )
        script_filename = f"pipeline_{run_id}.py"
        storage.save_file(script_filename, script_content.encode("utf-8"))

        finished_at = datetime.now(timezone.utc)
        rows_after, cols_after = df_current.shape

        result = ExecutionResult(
            run_id=run_id,
            dataset_id=dataset_id,
            plan_id=plan_id,
            status="completed" if not errors else "completed_with_errors",
            started_at=started_at,
            finished_at=finished_at,
            rows_before=rows_before,
            rows_after=rows_after,
            columns_before=cols_before,
            columns_after=cols_after,
            applied_steps_count=len(applied_steps),
            input_hash_md5=input_md5,
            output_hash_md5=output_md5,
            clean_filename=clean_filename,
            download_url=f"/api/v1/runs/{run_id}/download",
            script_url=f"/api/v1/runs/{run_id}/download-script",
            parquet_filename=parquet_filename,
            parquet_url=f"/api/v1/runs/{run_id}/download-parquet",
            audit_logs=audit_logs,
            errors=errors,
            warnings=warnings,
        )

        metadata.status = ProcessingStateEnum.COMPLETED
        RUNS_CACHE[run_id] = result
        return result

    @staticmethod
    def get_run_result(run_id: str) -> ExecutionResult:
        if run_id in RUNS_CACHE:
            return RUNS_CACHE[run_id]
        raise FunctionalException(
            message=f"La ejecución '{run_id}' no fue encontrada.", code="RUN_NOT_FOUND", status_code=404
        )
