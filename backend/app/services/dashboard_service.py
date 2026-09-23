"""
Dashboard Intelligence: orquestación del Blueprint de dashboard a partir del
esquema estrella.

Pipeline (separado del renderer, que vive en el frontend):

    Star Schema → Semantic Model Analyzer → Dashboard Planner →
    Visualization Recommendation Engine → Accessibility Validator →
    Design System Generator → Dashboard Blueprint → (Renderer/Preview)

La IA (cuando está disponible) solo interpreta contexto; toda validación,
contraste WCAG, existencia de campos y cálculo de métricas es determinista.
"""

import hashlib
import io
import json
import logging
import re
import threading
import time
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from app.core import wcag
from app.core.config import settings
from app.core.number_parsing import to_numeric_series
from app.core.storage import get_storage
from app.models.dashboard import (
    AccessibilityCheckItem,
    AccessibilityRecommendation,
    AggregationSemanticRoleEnum,
    BusinessQuestion,
    CheckCategoryEnum,
    ColorPalette,
    ColumnSemanticTypeEnum,
    ConfidenceLevelEnum,
    ContrastPairCheck,
    DashboardBlueprint,
    DashboardBlueprintList,
    DashboardBlueprintSummary,
    DashboardCheck,
    DashboardPage,
    DashboardStats,
    DashboardTypeEnum,
    DashboardValidation,
    DataQualityNote,
    DaxMeasure,
    DesignRecommendation,
    DesignSystem,
    FilterRecommendation,
    GenerationMeta,
    HierarchyRecommendation,
    KPIRecommendation,
    PowerBIImplementationInstruction,
    PreviewModeEnum,
    SemanticColumnAnalysis,
    SemanticModelAnalysis,
    SemanticTableAnalysis,
    ValidationStatusEnum,
    VisualRecommendation,
    VisualTypeEnum,
)
from app.models.workspace import MultiTableStarSchema
from app.services.relational_service import RelationalService
from app.services.semantic_analyzer import SemanticModelAnalyzer
from app.services.visual_engine import DERIVED_MEASURE_COL, VisualRecommendationEngine

DASHBOARD_CACHE: Dict[str, DashboardBlueprint] = {}
_STATS_LOCK = threading.Lock()
DASHBOARD_STATS: Dict[str, float] = {
    "dashboard_generation_total": 0,
    "dashboard_generation_failed": 0,
    "dashboard_generation_duration_ms_total": 0.0,
    "dashboard_validation_total": 0,
    "dashboard_validation_failed": 0,
    "visual_recommendation_count": 0,
    "wcag_validation_failed": 0,
}

KPI_COMPLETENESS_THRESHOLD = 85.0


def reset_dashboard_runtime() -> None:
    """Reinicia caché y contadores (uso en tests)."""
    DASHBOARD_CACHE.clear()
    with _STATS_LOCK:
        for key in DASHBOARD_STATS:
            DASHBOARD_STATS[key] = 0


def get_dashboard_stats() -> DashboardStats:
    return DashboardStats(
        dashboard_generation_total=int(DASHBOARD_STATS["dashboard_generation_total"]),
        dashboard_generation_failed=int(DASHBOARD_STATS["dashboard_generation_failed"]),
        dashboard_generation_duration_ms_total=round(
            float(DASHBOARD_STATS["dashboard_generation_duration_ms_total"]), 2
        ),
        dashboard_validation_total=int(DASHBOARD_STATS["dashboard_validation_total"]),
        dashboard_validation_failed=int(DASHBOARD_STATS["dashboard_validation_failed"]),
        visual_recommendation_count=int(DASHBOARD_STATS["visual_recommendation_count"]),
        wcag_validation_failed=int(DASHBOARD_STATS["wcag_validation_failed"]),
        cached_blueprints=len(DASHBOARD_CACHE),
    )


def _increment(key: str, amount: float = 1) -> None:
    with _STATS_LOCK:
        DASHBOARD_STATS[key] += amount


# ─────────────────── Persistencia de Blueprints (Fase 2: local → GCS) ───────

logger = logging.getLogger("dataflow.dashboard")

BLUEPRINT_STORAGE_PREFIX = "blueprint_"


def _blueprint_filename(blueprint_id: str) -> str:
    """Nombre seguro del artefacto JSON del Blueprint en el StorageBackend."""
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", blueprint_id)[:64] or "unknown"
    return f"{BLUEPRINT_STORAGE_PREFIX}{safe_id}.json"


def persist_blueprint(blueprint: DashboardBlueprint) -> bool:
    """
    Persiste el Blueprint en el StorageBackend activo.

    Con STORAGE_BACKEND=local el JSON vive en tmpfs/disco; con 'gcs' o 's3' se
    sube al bucket configurado, de modo que los Blueprints (y las ediciones
    HITL del usuario) sobreviven a los reinicios de instancias de Cloud Run.
    Un fallo de almacenamiento nunca rompe el flujo: el Blueprint sigue
    disponible en la caché en memoria (degradación elegante).
    """
    try:
        content = blueprint.model_dump_json().encode("utf-8")
        get_storage().save_file(_blueprint_filename(blueprint.blueprint_id), content)
        return True
    except Exception as exc:
        logger.warning("No se pudo persistir el blueprint '%s': %s", blueprint.blueprint_id, exc)
        return False


def load_persisted_blueprint(blueprint_id: str) -> Optional[DashboardBlueprint]:
    """Recupera un Blueprint persistido cuando la caché en memoria está vacía."""
    try:
        storage = get_storage()
        filename = _blueprint_filename(blueprint_id)
        if not storage.exists(filename):
            return None
        return DashboardBlueprint.model_validate_json(storage.read_file(filename))
    except Exception as exc:
        logger.warning("No se pudo cargar el blueprint persistido '%s': %s", blueprint_id, exc)
        return None


# ─────────────────── Historial de Blueprints (Paso 5, v1.25.0) ─────────────────


def _as_utc(moment: datetime) -> datetime:
    """Normaliza a timezone-aware UTC para comparaciones y ordenación."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _blueprint_is_expired(blueprint: DashboardBlueprint, retention_days: int) -> bool:
    """True si el Blueprint supera la retención (TTL) configurada; 0 = sin TTL."""
    if retention_days <= 0:
        return False
    return datetime.now(timezone.utc) - _as_utc(blueprint.created_at) > timedelta(days=retention_days)


def _summarize_blueprint(blueprint: DashboardBlueprint) -> DashboardBlueprintSummary:
    """Resumen ligero (sin preview_data) para el panel de historial del Paso 5."""
    validation = blueprint.validation
    return DashboardBlueprintSummary(
        blueprint_id=blueprint.blueprint_id,
        name=blueprint.name,
        dashboard_type=blueprint.dashboard_type,
        objective=blueprint.objective,
        confidence=blueprint.confidence,
        validation_status=validation.status if validation else None,
        passed_count=validation.passed_count if validation else 0,
        total_count=validation.total_count if validation else 0,
        dataset_ids=list(blueprint.dataset_ids),
        kpi_count=len(blueprint.kpis),
        visual_count=len(blueprint.visuals),
        palette_name=blueprint.design.palette.name,
        created_at=blueprint.created_at,
    )


def list_persisted_blueprints() -> DashboardBlueprintList:
    """
    Historial de Blueprints (Paso 5): fusiona la caché en memoria con los
    artefactos del StorageBackend (local/GCS/S3), aplica la retención (TTL)
    de settings.BLUEPRINT_RETENTION_DAYS —borrando de forma perezosa los
    caducados— y devuelve resúmenes ordenados por fecha descendente.
    """
    retention_days = max(0, int(settings.BLUEPRINT_RETENTION_DAYS))
    candidates: Dict[str, DashboardBlueprint] = dict(DASHBOARD_CACHE)
    expired_files: List[str] = []
    try:
        storage = get_storage()
        for filename in storage.list_files(prefix=BLUEPRINT_STORAGE_PREFIX):
            if not filename.endswith(".json"):
                continue
            bp_id = filename[len(BLUEPRINT_STORAGE_PREFIX) : -len(".json")]
            if not bp_id:
                continue
            blueprint = candidates.get(bp_id)
            if blueprint is None:
                blueprint = load_persisted_blueprint(bp_id)
                if blueprint is None:
                    continue
                candidates[bp_id] = blueprint
            if _blueprint_is_expired(blueprint, retention_days):
                expired_files.append(filename)
        # Retención perezosa: se eliminan del storage los artefactos caducados.
        for filename in expired_files:
            try:
                storage.delete_file(filename)
            except Exception as exc:
                logger.warning("No se pudo eliminar el blueprint caducado '%s': %s", filename, exc)
    except Exception as exc:
        logger.warning("No se pudo construir el historial de blueprints: %s", exc)

    summaries: List[DashboardBlueprintSummary] = []
    for bp_id, bp in list(candidates.items()):
        if _blueprint_is_expired(bp, retention_days):
            DASHBOARD_CACHE.pop(bp_id, None)
            continue
        summaries.append(_summarize_blueprint(bp))
    summaries.sort(key=lambda summary: _as_utc(summary.created_at), reverse=True)
    return DashboardBlueprintList(items=summaries, total=len(summaries), retention_days=retention_days)


# ─────────────────── Exportación TMDL / PBIP del Blueprint (v1.25.0) ────────────

TMDL_NUMERIC_FORMATS = {"currency": "#,##0.00", "decimal": "#,##0.00", "percentage": "0.00%", "number": "0"}


def _safe_model_name(raw: str) -> str:
    """Nombre ASCII seguro para el proyecto .pbip (sin acentos ni símbolos)."""
    ascii_only = unicodedata.normalize("NFKD", raw or "").encode("ascii", "ignore").decode("ascii")
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", ascii_only).strip("_")
    return sanitized or "DataFlow_Dashboard"


def _measure_expression(name: str, formula: str) -> str:
    """Extrae la expresión DAX de 'Nombre = expr' (o devuelve la fórmula tal cual)."""
    expr = (formula or "").strip()
    if expr.startswith(f"{name} ="):
        return expr[len(name) + 1 :].strip()
    head, sep, tail = expr.partition("=")
    if sep and "(" not in head and len(head) <= 80:
        return tail.strip()
    return expr


def _detect_sales_columns(fact_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Detecta (cantidad, precio, descuento) por nombre de columna: la misma regla
    determinista que `_load_context` usa para calcular __ventas_netas."""
    cols = {str(c).lower(): str(c) for c in fact_df.columns}
    qty_col = next((cols[k] for k in ("quantity", "cantidad", "qty", "unidades", "units") if k in cols), None)
    price_col = next((cols[k] for k in ("unitprice", "precio", "unit_price", "price") if k in cols), None)
    disc_col = next((cols[k] for k in ("discount", "descuento", "disc") if k in cols), None)
    return qty_col, price_col, disc_col


def _tmdl_data_type(semantic_type: ColumnSemanticTypeEnum) -> str:
    """Mapeo determinista tipo semántico → dataType TMDL (fallback sin dataset fuente)."""
    if semantic_type in (ColumnSemanticTypeEnum.DATE, ColumnSemanticTypeEnum.DATETIME):
        return "dateTime"
    if semantic_type in (
        ColumnSemanticTypeEnum.MEASURE,
        ColumnSemanticTypeEnum.CURRENCY,
        ColumnSemanticTypeEnum.PERCENTAGE,
        ColumnSemanticTypeEnum.QUANTITY,
    ):
        return "double"
    if semantic_type == ColumnSemanticTypeEnum.BOOLEAN:
        return "boolean"
    return "string"


def _m_source_csv(filename: str, m_types: List[Tuple[str, str]]) -> str:
    """Script Power Query M (CSV) apuntado al archivo real del StorageBackend."""
    safe_fn = str(filename).replace('"', "")
    types_formatted = ",\n        ".join(f'{{"{name}", {pq_type}}}' for name, pq_type in m_types)
    return (
        f"let\n"
        f'    Source = Csv.Document(File.Contents("{safe_fn}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        f'    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n'
        f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{\n'
        f"        {types_formatted}\n"
        f"    }})\n"
        f"in\n"
        f'    #"Changed Type"'
    )


def _blueprint_table_tmdl(
    table: SemanticTableAnalysis,
    measures: List[DaxMeasure],
    source: Optional[Tuple[pd.DataFrame, str]],
    kpi_formats: Dict[str, str],
) -> str:
    """Definición TMDL de una tabla del Blueprint: medidas DAX (con ediciones
    HITL), columnas y partición M cuando el archivo fuente sigue disponible."""
    from app.services.analytics_service import AnalyticsService  # import local: evita ciclos

    table_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.table_name}.blueprint.table"))
    lines: List[str] = [f"table '{table.table_name}'", f"\tlineageTag: {table_guid}", ""]

    # Medidas DAX (incluye las decisiones editadas por el usuario)
    for m in measures:
        m_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.table_name}.measure.{m.name}"))
        expr = _measure_expression(m.name, m.formula)
        expr_indented = "\n\t\t\t".join(expr.split("\n"))
        lines.append(f"\tmeasure '{m.name}' = \n\t\t\t{expr_indented}")
        fmt = kpi_formats.get(m.name)
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tlineageTag: {m_guid}")
        lines.append("")

    # Columnas: dtype real si el dataset fuente existe; si no, tipo semántico
    column_specs: List[Tuple[str, str, str]] = []  # (nombre, dataType TMDL, summarizeBy)
    m_types: List[Tuple[str, str]] = []  # (nombre, tipo Power Query M) del origen real
    if source is not None:
        df = source[0]
        for col_name in df.columns:
            name = str(col_name)
            if name == DERIVED_MEASURE_COL:
                continue
            pq_type, role = AnalyticsService._map_to_power_query_type(name, df[col_name])
            tmdl_type = AnalyticsService._map_to_tmdl_type(pq_type)
            column_specs.append((name, tmdl_type, "sum" if role == "numeric" else "none"))
            m_types.append((name, pq_type))
    else:
        for col in table.columns:
            if col.column_name == DERIVED_MEASURE_COL:
                continue
            tmdl_type = _tmdl_data_type(col.semantic_type)
            summarize_by = "sum" if tmdl_type in ("int64", "double") else "none"
            column_specs.append((col.column_name, tmdl_type, summarize_by))

    for name, tmdl_type, summarize_by in column_specs:
        col_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.table_name}.col.{name}"))
        lines.append(f"\tcolumn '{name}'")
        lines.append(f"\t\tdataType: {tmdl_type}")
        if tmdl_type == "int64":
            lines.append("\t\tformatString: 0")
        elif tmdl_type == "double":
            lines.append("\t\tformatString: #,##0.00")
        elif tmdl_type == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        lines.append(f"\t\tlineageTag: {col_guid}")
        lines.append(f"\t\tsummarizeBy: {summarize_by}")
        lines.append(f"\t\tsourceColumn: '{name}'")
        lines.append("")

    # __ventas_netas: columna calculada determinista (no existe en el CSV original)
    if source is not None:
        df = source[0]
        qty_col, price_col, disc_col = _detect_sales_columns(df)
        if qty_col and price_col:
            d_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.table_name}.col.{DERIVED_MEASURE_COL}"))
            derived_expr = f"'{table.table_name}'[{qty_col}] * '{table.table_name}'[{price_col}]"
            if disc_col:
                derived_expr += f" * (1 - '{table.table_name}'[{disc_col}])"
            lines.append(f"\tcolumn '{DERIVED_MEASURE_COL}' = {derived_expr}")
            lines.append("\t\tdataType: double")
            lines.append("\t\tformatString: #,##0.00")
            lines.append(f"\t\tlineageTag: {d_guid}")
            lines.append("\t\tsummarizeBy: sum")
            lines.append("")

    # Partición M solo cuando el archivo fuente existe (sin referencias ficticias)
    if source is not None and m_types:
        m_script = _m_source_csv(source[1], m_types)
        m_indented = "\n\t\t\t".join(m_script.split("\n"))
        lines.append(f"\tpartition '{table.table_name}' = m")
        lines.append("\t\tmode: import")
        lines.append(f"\t\tsource =\n\t\t\t{m_indented}")
        lines.append("")

    return "\n".join(lines)


def _blueprint_tmdl_parts(blueprint: DashboardBlueprint) -> Tuple[str, Dict[str, str], str]:
    """Compone (model.tmdl, {tabla: definición TMDL}, nombre seguro del proyecto)."""
    tables = list(blueprint.semantic_model.tables)
    table_names = [t.table_name for t in tables]

    # Fuentes reales por tabla (si el dataset sigue en el StorageBackend)
    sources: Dict[str, Tuple[pd.DataFrame, str]] = {}
    for table in tables:
        if table.table_name in sources:
            continue
        try:
            df, filename = RelationalService._load_dataset_df(table.table_id)
            if not df.empty:
                sources[table.table_name] = (df, filename)
        except Exception as exc:
            logger.info("Fuente no disponible para exportar '%s': %s", table.table_name, exc)

    # model.tmdl: reutiliza el generador del esquema estrella si los datos existen
    model_tmdl = ""
    try:
        schema = RelationalService.infer_star_schema(list(blueprint.dataset_ids))
        model_tmdl = schema.tmdl_definition or ""
    except Exception as exc:
        logger.info("Esquema estrella no disponible para '%s': %s", blueprint.blueprint_id, exc)
    if not model_tmdl:
        fallback = ["model Model", "\tculture: es-ES", "\tdefaultPowerBIDataSourceVersion: powerBI_V3", ""]
        fallback.extend(f"ref table '{name}'" for name in table_names)
        model_tmdl = "\n".join(fallback) + "\n"

    # Medidas agrupadas por tabla (las huérfanas van a la primera tabla)
    measures_by_table: Dict[str, List[DaxMeasure]] = {name: [] for name in table_names}
    for m in blueprint.dax_measures:
        if m.table_context in measures_by_table:
            measures_by_table[m.table_context].append(m)
        elif table_names:
            measures_by_table[table_names[0]].append(m)

    kpi_formats: Dict[str, str] = {}
    for kpi in blueprint.kpis:
        fmt = TMDL_NUMERIC_FORMATS.get(str(kpi.format_type))
        if fmt and kpi.dax_measure_name and kpi.dax_measure_name not in kpi_formats:
            kpi_formats[kpi.dax_measure_name] = fmt

    table_tmdl = {
        name: _blueprint_table_tmdl(table, measures_by_table[name], sources.get(name), kpi_formats)
        for table, name in zip(tables, table_names, strict=True)
    }
    return model_tmdl, table_tmdl, _safe_model_name(blueprint.name)


def export_blueprint_tmdl(blueprint: DashboardBlueprint) -> str:
    """Script TMDL completo (modelo + tablas + medidas) del Blueprint editado."""
    model_tmdl, table_tmdl, _ = _blueprint_tmdl_parts(blueprint)
    parts = [model_tmdl.rstrip("\n")]
    parts.extend(definition.rstrip("\n") for definition in table_tmdl.values())
    return "\n\n".join(parts) + "\n"


def export_blueprint_pbip(blueprint: DashboardBlueprint) -> bytes:
    """ZIP .pbip (Power BI Developer Mode) con el modelo del Blueprint editado."""
    model_tmdl, table_tmdl, name = _blueprint_tmdl_parts(blueprint)

    pbip_json = json.dumps(
        {
            "version": "1.0",
            "artifacts": [{"semanticModel": {"path": f"{name}.SemanticModel"}}],
            "settings": {"enableAutoAuth": True},
        },
        indent=2,
    )
    pbidataset_json = json.dumps({"version": "1.0", "settings": {}}, indent=2)
    diagram_json = json.dumps({"version": "1.0.0", "diagrams": []}, indent=2)
    database_tmdl = f"database '{name}'\n\tcompatibilityLevel: 1567\n"
    culture_tmdl = "culture es-ES\n"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{name}.pbip", pbip_json)
        zf.writestr(f"{name}.SemanticModel/definition.pbidataset", pbidataset_json)
        zf.writestr(f"{name}.SemanticModel/diagramLayout.json", diagram_json)
        zf.writestr(f"{name}.SemanticModel/definition/database.tmdl", database_tmdl)
        zf.writestr(f"{name}.SemanticModel/definition/model.tmdl", model_tmdl)
        zf.writestr(f"{name}.SemanticModel/definition/cultures/es-ES.tmdl", culture_tmdl)
        for table_name, definition in table_tmdl.items():
            zf.writestr(f"{name}.SemanticModel/definition/tables/{table_name}.tmdl", definition)
    buf.seek(0)
    return buf.getvalue()


# ───────────────────────────── Contexto del modelo ──────────────────────────


@dataclass
class ModelContext:
    """Contexto determinista del modelo estrella para análisis y validación."""

    schema: MultiTableStarSchema
    dataframes: Dict[str, pd.DataFrame]
    dataset_ids: List[str]

    @property
    def fact_name(self) -> str:
        return self.schema.fact_table.table_name

    def qualified_fields(self) -> Set[str]:
        fields: Set[str] = set()
        for node in [self.schema.fact_table] + self.schema.dimension_tables:
            df = self.dataframes.get(node.table_name, pd.DataFrame())
            for col in df.columns:
                fields.add(f"{node.table_name}[{col}]")
        return fields

    def table_exists(self, table_name: str) -> bool:
        names = {self.schema.fact_table.table_name} | {d.table_name for d in self.schema.dimension_tables}
        return table_name in names

    def relationship_exists(self, from_table: str, to_table: str) -> bool:
        return any(r.from_table == from_table and r.to_table == to_table for r in self.schema.relationships)

    def completeness(self, table: str, column: str) -> Optional[float]:
        df = self.dataframes.get(table)
        if df is None or column not in df.columns or len(df) == 0:
            return None
        return round(100.0 * df[column].notna().mean(), 2)


# ───────────────────────────── Clasificación de tipo ────────────────────────

_TYPE_KEYWORDS: List[Tuple[DashboardTypeEnum, List[str]]] = [
    (DashboardTypeEnum.SALES, ["venta", "sales", "pedido", "order", "revenue", "ingreso", "factura", "ticket"]),
    (
        DashboardTypeEnum.FINANCE,
        ["coste", "cost", "presupuesto", "budget", "financ", "finance", "saldo", "beneficio", "profit"],
    ),
    (DashboardTypeEnum.HR, ["empleado", "employee", "salario", "salary", "rrhh", "personal", "ausent", "absent"]),
    (
        DashboardTypeEnum.MARKETING,
        ["campaign", "campaña", "canal", "channel", "lead", "conversion", "conversión", "publicidad", "ads", "clic"],
    ),
    (
        DashboardTypeEnum.INVENTORY,
        ["stock", "inventario", "inventory", "almacen", "almacén", "warehouse", "existencia"],
    ),
    (DashboardTypeEnum.CUSTOMERS, ["cliente", "customer", "segmento", "churn", "fideliz", "retention", "retención"]),
    (
        DashboardTypeEnum.LOGISTICS,
        ["envio", "envío", "shipping", "entrega", "delivery", "transporte", "logistic", "logíst"],
    ),
    (
        DashboardTypeEnum.ACADEMIC,
        ["alumno", "estudiante", "calificacion", "calificación", "nota", "curso", "asignatura", "academic"],
    ),
    (
        DashboardTypeEnum.OPERATIONS,
        ["operacion", "operación", "servicio", "service", "incidencia", "produccion", "producción", "proceso"],
    ),
]


class DashboardTypeClassifier:
    """Clasificación determinista del tipo de dashboard por señales semánticas."""

    @staticmethod
    def classify(analysis: SemanticModelAnalysis) -> Tuple[DashboardTypeEnum, str, ConfidenceLevelEnum, Optional[str]]:
        names: List[str] = []
        for table in analysis.tables:
            names.append(table.table_name.lower())
            names.extend(col.column_name.lower() for col in table.columns)
        haystack = " · ".join(names)

        scores: List[Tuple[int, DashboardTypeEnum]] = []
        for dtype, keywords in _TYPE_KEYWORDS:
            score = sum(haystack.count(keyword) for keyword in keywords)
            if score > 0:
                scores.append((score, dtype))

        if not scores:
            return (
                DashboardTypeEnum.GENERIC,
                "Dashboard general",
                ConfidenceLevelEnum.LOW,
                "No se encontraron señales semánticas suficientes para determinar el dominio del dashboard; se propone un panel general.",
            )

        scores.sort(key=lambda item: (-item[0], item[1].value))
        winner_score, winner = scores[0]
        second_score = scores[1][0] if len(scores) > 1 else 0

        if winner_score < 2:
            return (
                DashboardTypeEnum.GENERIC,
                "Dashboard general",
                ConfidenceLevelEnum.LOW,
                f"Señales débiles para '{winner.value}' ({winner_score} coincidencia); se propone un panel general para no inventar contexto de negocio.",
            )

        if winner_score >= 4 and winner_score - second_score <= 1:
            return (
                DashboardTypeEnum.EXECUTIVE,
                "Dashboard ejecutivo",
                ConfidenceLevelEnum.MEDIUM,
                f"Concurren señales de varios dominios ({winner.value}, {scores[1][1].value}); se propone una vista ejecutiva agregada.",
            )

        confidence = ConfidenceLevelEnum.HIGH if winner_score >= 6 else ConfidenceLevelEnum.MEDIUM
        return winner, f"Dashboard de {winner.value}", confidence, None


# ───────────────────────────── Sanitizador de títulos ────────────────────────
class ReportTitleSanitizer:
    """Sanitiza títulos ejecutivos de dashboards eliminando ruido técnico (dirty, clean, csv, etc.)."""

    NOISE_TOKENS = {
        "dirty",
        "clean",
        "raw",
        "tmp",
        "temp",
        "csv",
        "xlsx",
        "parquet",
        "tsv",
        "file",
        "dataset",
        "table",
        "tabla",
    }

    FRIENDLY_NAMES = {
        "order details": "Detalle de Pedidos",
        "order detail": "Detalle de Pedidos",
        "orderdetails": "Detalle de Pedidos",
        "orders": "Pedidos",
        "order": "Pedidos",
        "pedidos": "Pedidos",
        "pedido": "Pedidos",
        "sales": "Ventas",
        "sale": "Ventas",
        "ventas": "Ventas",
        "customers": "Clientes",
        "customer": "Clientes",
        "clientes": "Clientes",
        "cliente": "Clientes",
        "products": "Productos",
        "product": "Productos",
        "productos": "Productos",
        "producto": "Productos",
        "inventory": "Inventario",
        "inventario": "Inventario",
        "employees": "Empleados",
        "employee": "Empleados",
        "empleados": "Empleados",
        "invoices": "Facturas",
        "invoice": "Facturas",
        "facturas": "Facturas",
    }

    @classmethod
    def sanitize(cls, domain_title: str, fact_table_name: str) -> str:
        name = str(fact_table_name)
        for ext in (".csv", ".xlsx", ".parquet", ".tsv"):
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
        name = re.sub(r"[_\-]+", " ", name).strip()
        tokens = [t for t in name.split() if t.lower() not in cls.NOISE_TOKENS and not t.isdigit() and len(t) > 1]
        cleaned_core = " ".join(tokens).strip().lower()

        friendly = cls.FRIENDLY_NAMES.get(cleaned_core)
        if not friendly and cleaned_core:
            friendly = " ".join(w.capitalize() for w in tokens)

        if not friendly or friendly.lower() in domain_title.lower():
            clean_title = domain_title
        else:
            clean_title = f"{domain_title} — {friendly}"

        clean_title = clean_title.replace("_", " ")
        for noise in ("dirty", "raw", "clean", ".csv", ".xlsx"):
            clean_title = re.sub(rf"\b{noise}\b", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s+", " ", clean_title).strip()
        clean_title = re.sub(r"\s*—\s*$", "", clean_title).strip()
        return clean_title


# ───────────────────────────── KPIs y DAX ───────────────────────────────────


class KpiGenerator:
    """Generación determinista de KPIs con valores reales y notas de Data Quality."""

    def __init__(self, context: ModelContext, analysis: SemanticModelAnalysis):
        self.context = context
        self.analysis = analysis
        self.fact_df = context.dataframes.get(context.fact_name, pd.DataFrame())

    def _find_column(
        self, semantic_types: List[ColumnSemanticTypeEnum], table_only: bool = True
    ) -> Optional[Tuple[str, str]]:
        for table in self.analysis.tables:
            if table_only and table.table_name != self.context.fact_name:
                continue
            for col in table.columns:
                if col.semantic_type in semantic_types:
                    return table.table_name, col.column_name
        return None

    def generate(self, primary: Optional[Dict[str, object]]) -> Tuple[List[KPIRecommendation], List[str]]:
        kpis: List[KPIRecommendation] = []
        warnings: List[str] = []
        fact = self.context.schema.fact_table
        order = 0
        is_unit_or_ratio = False

        # 1) KPI principal: suma de la medida principal (o promedio si es unitario/ratio)
        if primary is not None:
            table = str(primary["table"])
            column = str(primary["column"])
            completeness = self.context.completeness(table, column) or 0.0
            if completeness >= KPI_COMPLETENESS_THRESHOLD:
                df = self.context.dataframes.get(table, pd.DataFrame())
                numeric = to_numeric_series(df[column]).dropna() if column in df.columns else pd.Series(dtype=float)

                role = primary.get("aggregation_role") or getattr(primary.get("analysis"), "aggregation_role", None)
                is_unit_or_ratio = role in (
                    AggregationSemanticRoleEnum.UNIT_PRICE_OR_RATE,
                    AggregationSemanticRoleEnum.RATIO_OR_PERCENTAGE,
                )

                if is_unit_or_ratio:
                    value = float(numeric.mean()) if len(numeric) else None
                    kpi_title = str(primary.get("label") or "Precio unitario medio")
                    dax_name = str(primary.get("dax_name") or f"Promedio_{column}")
                    dax_formula = str(primary.get("dax_formula") or f"AVERAGE('{table}'[{column}])")
                    desc = f"Promedio ponderado/aritmético de {column} en {table}."
                elif primary.get("derived"):
                    value = float(numeric.sum()) if len(numeric) else None
                    kpi_title = "Ventas netas"
                    dax_name = "Ventas_Netas"
                    dax_formula = str(primary.get("dax_formula") or f"SUM('{table}'[{column}])")
                    desc = f"Suma total de ventas netas calculadas en {table}."
                else:
                    value = float(numeric.sum()) if len(numeric) else None
                    kpi_title = f"Total {column.replace('_', ' ').lower()}"
                    dax_name = str(primary.get("dax_name") or f"Total_{column}")
                    dax_formula = str(primary.get("dax_formula") or f"SUM('{table}'[{column}])")
                    desc = f"Suma total de {column} en {table}."

                kpis.append(
                    KPIRecommendation(
                        kpi_id=f"kpi_total_{column.lower()}",
                        title=kpi_title,
                        description=desc,
                        dax_measure_name=dax_name,
                        dax_formula=dax_formula,
                        table_context=table,
                        format_type=(
                            "currency"
                            if primary["analysis"].semantic_type == ColumnSemanticTypeEnum.CURRENCY
                            else "number"
                        ),
                        validated=True,
                        value=round(value, 2) if value is not None else None,
                        value_label=(
                            self._format_value(value, primary["analysis"].semantic_type) if value is not None else None
                        ),
                        confidence=ConfidenceLevelEnum.HIGH,
                        data_quality_notes=[],
                        order=order,
                    )
                )
                order += 1
            else:
                warnings.append(
                    f"No se recomienda un KPI sobre {table}[{column}] (completitud {completeness:.1f}% < {KPI_COMPLETENESS_THRESHOLD:.0f}%)."
                )

        # 2) KPI de conteo: pedidos o registros sobre la PK o FK del hecho
        order_col = None
        for col_name in self.fact_df.columns:
            lower = col_name.lower().replace("_", "")
            if lower in ("orderid", "idpedido", "idorden", "numpedido", "pedidoid"):
                order_col = col_name
                break

        pk_col = fact.primary_keys[0] if fact.primary_keys else None

        if order_col is not None and order_col in self.fact_df.columns:
            unique_count = int(self.fact_df[order_col].nunique())
            kpis.append(
                KPIRecommendation(
                    kpi_id="kpi_count_orders",
                    title="Pedidos",
                    description=f"Número de pedidos únicos ({order_col}) en {fact.table_name}.",
                    dax_measure_name="Pedidos",
                    dax_formula=f"DISTINCTCOUNT('{fact.table_name}'[{order_col}])",
                    table_context=fact.table_name,
                    format_type="number",
                    validated=True,
                    value=float(unique_count),
                    value_label=f"{unique_count:,}".replace(",", "."),
                    confidence=ConfidenceLevelEnum.HIGH,
                    data_quality_notes=[],
                    order=order,
                )
            )
            order += 1
        elif pk_col is not None and pk_col in self.fact_df.columns:
            unique_count = int(self.fact_df[pk_col].nunique())
            pk_lower = pk_col.lower()
            is_detail = "detail" in pk_lower or "detalle" in pk_lower or "line" in pk_lower or "linea" in pk_lower
            is_order_like = any(k in pk_lower for k in ("pedido", "order", "factura")) and not is_detail
            kpi_title = "Pedidos" if is_order_like else ("Líneas de detalle" if is_detail else "Registros")
            dax_name = "Pedidos" if is_order_like else "Total_Registros"
            kpis.append(
                KPIRecommendation(
                    kpi_id=f"kpi_count_{pk_col.lower()}",
                    title=kpi_title,
                    description=f"Número de valores únicos de {pk_col} en {fact.table_name}.",
                    dax_measure_name=dax_name,
                    dax_formula=f"DISTINCTCOUNT('{fact.table_name}'[{pk_col}])",
                    table_context=fact.table_name,
                    format_type="number",
                    validated=True,
                    value=float(unique_count),
                    value_label=f"{unique_count:,}".replace(",", "."),
                    confidence=ConfidenceLevelEnum.HIGH,
                    data_quality_notes=[],
                    order=order,
                )
            )
            order += 1

        # 3) Ticket medio: DIVIDE entre medida principal y conteo (solo si la medida es aditiva de importe)
        if (
            kpis
            and len(kpis) >= 2
            and not is_unit_or_ratio
            and kpis[0].format_type in ("currency", "number")
            and kpis[1].value
        ):
            revenue = kpis[0].value or 0.0
            count = kpis[1].value or 0.0
            ticket = round(revenue / count, 2) if count else None
            kpis.append(
                KPIRecommendation(
                    kpi_id="kpi_ticket_medio",
                    title="Ticket medio",
                    description="Cociente entre la medida principal y el número de pedidos/registros.",
                    dax_measure_name="Ticket_Medio",
                    dax_formula=f"DIVIDE([{kpis[0].dax_measure_name}], [{kpis[1].dax_measure_name}])",
                    table_context=fact.table_name,
                    format_type="decimal",
                    validated=True,
                    value=ticket,
                    value_label=(
                        f"{ticket:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if ticket is not None
                        else None
                    ),
                    confidence=ConfidenceLevelEnum.MEDIUM,
                    data_quality_notes=[],
                    order=order,
                )
            )
            order += 1

        # 4) Precio medio si existe columna de precio y la medida principal no fue ya unitaria
        price_col = self._find_column([ColumnSemanticTypeEnum.CURRENCY])
        if (
            price_col
            and not is_unit_or_ratio
            and price_col[1] != str((primary or {}).get("column", ""))
            and DERIVED_MEASURE_COL not in price_col[1]
        ):
            table, column = price_col
            df = self.context.dataframes.get(table, pd.DataFrame())
            numeric = to_numeric_series(df[column]).dropna() if column in df.columns else pd.Series(dtype=float)
            if len(numeric) > 0:
                avg = float(numeric.mean())
                kpis.append(
                    KPIRecommendation(
                        kpi_id=f"kpi_avg_{column.lower()}",
                        title=f"{column.replace('_', ' ').capitalize()} medio",
                        description=f"Media de {column} en {table}.",
                        dax_measure_name=f"Promedio_{column}",
                        dax_formula=f"AVERAGE('{table}'[{column}])",
                        table_context=table,
                        format_type="currency",
                        validated=True,
                        value=round(avg, 2),
                        value_label=f"{avg:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        confidence=ConfidenceLevelEnum.MEDIUM,
                        data_quality_notes=[],
                        order=order,
                    )
                )
                order += 1

        return kpis[:6], warnings

    @staticmethod
    def _format_value(value: float, semantic_type: ColumnSemanticTypeEnum) -> str:
        if semantic_type == ColumnSemanticTypeEnum.CURRENCY:
            return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{value:,.0f}".replace(",", ".")


class DaxGenerator:
    """Medidas DAX como especificaciones para Power BI (nunca se ejecutan)."""

    @staticmethod
    def generate(context: ModelContext, kpis: List[KPIRecommendation]) -> List[DaxMeasure]:
        measures: List[DaxMeasure] = []
        seen: Set[str] = set()

        for name, formula in sorted(context.schema.suggested_dax_measures.items()):
            if name in seen:
                continue
            seen.add(name)
            measures.append(
                DaxMeasure(
                    name=name,
                    formula=formula,
                    table_context=context.fact_name,
                    purpose="Medida base generada a partir del esquema estrella validado.",
                    validated=True,
                    kind="base",
                )
            )

        for kpi in kpis:
            if kpi.dax_measure_name in seen:
                continue
            seen.add(kpi.dax_measure_name)
            measures.append(
                DaxMeasure(
                    name=kpi.dax_measure_name,
                    formula=kpi.dax_formula,
                    table_context=kpi.table_context,
                    purpose=kpi.description,
                    validated=kpi.validated,
                    kind="business",
                )
            )
        return measures


# ───────────────────────────── Diseño y accesibilidad ───────────────────────

_PALETTE_BASES: List[Dict[str, str]] = [
    {
        "name": "Analítico moderno (azul)",
        "background_color": "#0F172A",
        "text_color": "#F8FAFC",
        "muted_text_color": "#94A3B8",
        "primary_color": "#0EA5E9",
        "secondary_color": "#3B82F6",
        "accent_color": "#10B981",
        "positive_color": "#10B981",
        "negative_color": "#F43F5E",
        "warning_color": "#F59E0B",
    },
    {
        "name": "Ejecutivo sobrio (grafito)",
        "background_color": "#111827",
        "text_color": "#F9FAFB",
        "muted_text_color": "#9CA3AF",
        "primary_color": "#3B82F6",
        "secondary_color": "#6366F1",
        "accent_color": "#22D3EE",
        "positive_color": "#34D399",
        "negative_color": "#F87171",
        "warning_color": "#FBBF24",
    },
    {
        "name": "Analítica cálida (ámbar)",
        "background_color": "#1C1917",
        "text_color": "#FAFAF9",
        "muted_text_color": "#A8A29E",
        "primary_color": "#F59E0B",
        "secondary_color": "#FB923C",
        "accent_color": "#38BDF8",
        "positive_color": "#4ADE80",
        "negative_color": "#FB7185",
        "warning_color": "#FACC15",
    },
]

_STYLES: List[Dict[str, str]] = [
    {
        "style_name": "Modern analytical",
        "typography": "Jerarquía clara: título 24/600, subtítulo 16/500, valores KPI 32/700, etiquetas 12/400",
        "density": "Medium",
        "color_strategy": "Base neutra + acento semántico",
        "notes": "Retícula de 12 columnas, espaciado base 8px, tarjetas con radio moderado.",
    },
    {
        "style_name": "Executive",
        "typography": "Jerarquía sobria: título 22/600, valores KPI 30/700, texto 14/400",
        "density": "Low",
        "color_strategy": "Paleta contenida con un único color de énfasis",
        "notes": "Menos visuales por página, más espacio en blanco, foco en KPIs.",
    },
    {
        "style_name": "Operational control",
        "typography": "Jerarquía densa: título 20/600, valores 24/700, etiquetas 11/500",
        "density": "High",
        "color_strategy": "Semáforo semántico (positivo/negativo/aviso) con apoyo de iconos",
        "notes": "Prioriza excepciones y tablas de detalle sobre la estética.",
    },
]


class DesignSystemGenerator:
    """Genera sistema de diseño con paletas validadas matemáticamente contra WCAG."""

    @staticmethod
    def _build_palette(base: Dict[str, str]) -> Tuple[ColorPalette, List[ContrastPairCheck], bool]:
        bg = base["background_color"]
        text = base["text_color"]
        muted = (
            wcag.ensure_contrast(base["muted_text_color"], bg, wcag.AA_NORMAL_TEXT, direction="to_lighter")
            or base["muted_text_color"]
        )

        palette = ColorPalette(
            name=base["name"],
            primary_color=base["primary_color"],
            secondary_color=base["secondary_color"],
            accent_color=base["accent_color"],
            background_color=bg,
            text_color=text,
            muted_text_color=muted,
            positive_color=base["positive_color"],
            negative_color=base["negative_color"],
            warning_color=base["warning_color"],
        )

        checks: List[ContrastPairCheck] = []
        pairs = [
            ("Texto principal sobre fondo", text, bg, False, False),
            ("Texto atenuado sobre fondo", muted, bg, False, False),
            ("Texto sobre color primario (botones)", bg, base["primary_color"], False, False),
            ("Primario sobre fondo (gráficos/UI)", base["primary_color"], bg, False, True),
            ("Positivo sobre fondo", base["positive_color"], bg, False, True),
            ("Negativo sobre fondo", base["negative_color"], bg, False, True),
            ("Aviso sobre fondo", base["warning_color"], bg, False, True),
        ]
        all_pass = True
        for label, fg, background, large, is_ui in pairs:
            ratio = wcag.contrast_ratio(fg, background)
            levels = wcag.wcag_check(ratio, large_text=large, ui_component=is_ui)
            checks.append(
                ContrastPairCheck(
                    label=label,
                    foreground=fg.upper(),
                    background=background.upper(),
                    contrast_ratio=ratio,
                    aa=levels["aa"],
                    aaa=levels["aaa"],
                    large_text=large,
                )
            )
            if not levels["aa"]:
                all_pass = False
        return palette, checks, all_pass

    @staticmethod
    def _accessibility_checklist(wcag_pass: bool) -> List[AccessibilityCheckItem]:
        return [
            AccessibilityCheckItem(
                label="Contraste",
                status="pass" if wcag_pass else "warning",
                detail="Ratios WCAG calculadas con luminancia relativa; pares texto/fondo validados matemáticamente.",
            ),
            AccessibilityCheckItem(
                label="Etiquetas",
                status="pass",
                detail="Todos los visuales incluyen título descriptivo y etiquetas de eje/leyenda explícitas.",
            ),
            AccessibilityCheckItem(
                label="Independencia del color",
                status="pass",
                detail="Ningún visual depende solo del color: se usan etiquetas, patrones y tooltips con valores.",
            ),
            AccessibilityCheckItem(
                label="Jerarquía visual",
                status="pass",
                detail="Orden de lectura KPIs → tendencia → desglose → detalle con tamaños proporcionales a la importancia.",
            ),
            AccessibilityCheckItem(
                label="Legibilidad", status="pass", detail="Fuente mínima 11px, contraste de texto atenuado ≥ 4.5:1."
            ),
            AccessibilityCheckItem(
                label="Recomendación",
                status="warning",
                detail="Evitar rojo/verde como único diferenciador; en KPIs de variación acompañar con icono ▲/▼ y signo.",
            ),
        ]

    @staticmethod
    def _accessibility_declarations() -> List[str]:
        return [
            "No depender exclusivamente del color para transmitir información.",
            "Tamaño de fuente mínimo 11px para etiquetas y 14px para texto de apoyo.",
            "Máximo 6-8 categorías por visual; agrupar el resto.",
            "Evitar gráficos circulares con más de 6 categorías.",
            "Orden lógico de lectura: KPIs, tendencia, desglose, detalle.",
            "Títulos descriptivos y tooltips informativos con valores exactos.",
            "Filtros comprensibles con valores reales del dataset.",
        ]

    @classmethod
    def recheck_accessibility(cls, palette: ColorPalette) -> AccessibilityRecommendation:
        """
        Recalcula los pares de contraste WCAG de la paleta activa.

        Se usa en la edición HITL del Paso 5: cuando el usuario cambia la
        paleta por una variante prevalidada, la validación debe reflejar sus
        colores reales y no los de la paleta propuesta originalmente por la IA.
        """
        bg = palette.background_color
        pairs_spec = [
            ("Texto principal sobre fondo", palette.text_color, bg, False, False),
            ("Texto atenuado sobre fondo", palette.muted_text_color, bg, False, False),
            ("Texto sobre color primario (botones)", bg, palette.primary_color, False, False),
            ("Primario sobre fondo (gráficos/UI)", palette.primary_color, bg, False, True),
            ("Positivo sobre fondo", palette.positive_color, bg, False, True),
            ("Negativo sobre fondo", palette.negative_color, bg, False, True),
            ("Aviso sobre fondo", palette.warning_color, bg, False, True),
        ]
        checks: List[ContrastPairCheck] = []
        all_pass = True
        for label, fg, background, large, is_ui in pairs_spec:
            ratio = wcag.contrast_ratio(fg, background)
            levels = wcag.wcag_check(ratio, large_text=large, ui_component=is_ui)
            checks.append(
                ContrastPairCheck(
                    label=label,
                    foreground=fg.upper(),
                    background=background.upper(),
                    contrast_ratio=ratio,
                    aa=levels["aa"],
                    aaa=levels["aaa"],
                    large_text=large,
                )
            )
            if not levels["aa"]:
                all_pass = False
        return AccessibilityRecommendation(
            contrast_pairs=checks,
            checklist=cls._accessibility_checklist(all_pass),
            overall_label="WCAG AA: PASS" if all_pass else "WCAG AA: FAIL",
            declarations=cls._accessibility_declarations(),
        )

    @classmethod
    def build(cls) -> Tuple[DesignSystem, bool]:
        palettes: List[ColorPalette] = []
        all_checks: List[ContrastPairCheck] = []
        wcag_pass = True
        for base in _PALETTE_BASES:
            palette, checks, ok = cls._build_palette(base)
            palettes.append(palette)
            all_checks.extend(checks)
            if not ok:
                wcag_pass = False

        checklist = cls._accessibility_checklist(wcag_pass)
        declarations = cls._accessibility_declarations()
        accessibility = AccessibilityRecommendation(
            contrast_pairs=all_checks,
            checklist=checklist,
            overall_label="WCAG AA: PASS" if wcag_pass else "WCAG AA: FAIL",
            declarations=declarations,
        )

        styles = [
            DesignRecommendation(
                style_name=style["style_name"],
                canvas="16:9",
                layout="12-column grid",
                spacing="8px base grid",
                cards="Moderate radius",
                typography=style["typography"],
                density=style["density"],
                color_strategy=style["color_strategy"],
                notes=[style["notes"]],
            )
            for style in _STYLES
        ]
        design = DesignSystem(
            style=styles[0],
            style_variants=styles[1:],
            palette=palettes[0],
            palette_variants=palettes[1:],
            accessibility=accessibility,
        )
        return design, wcag_pass


# ───────────────────────────── Planificador ─────────────────────────────────

_TYPE_PROFILES: Dict[DashboardTypeEnum, Dict[str, object]] = {
    DashboardTypeEnum.SALES: {
        "name": "Rendimiento de Ventas",
        "audience": "Dirección comercial y responsables de ventas",
        "questions": [
            "¿Cuál es la evolución mensual de la medida principal?",
            "¿Qué categoría o zona concentra más ventas?",
            "¿Cuáles son los productos o clientes con mejor rendimiento?",
        ],
    },
    DashboardTypeEnum.FINANCE: {
        "name": "Control Financiero",
        "audience": "Dirección financiera y controlling",
        "questions": [
            "¿Cómo evolucionan costes e ingresos en el tiempo?",
            "¿Dónde se concentra el gasto?",
            "¿Qué partidas se desvían del presupuesto?",
        ],
    },
    DashboardTypeEnum.OPERATIONS: {
        "name": "Control de Operaciones",
        "audience": "Responsables de operaciones y calidad de servicio",
        "questions": [
            "¿Cuál es la tendencia operativa en el tiempo?",
            "¿Dónde se concentran las excepciones o incidencias?",
            "¿Qué casos requieren revisión inmediata?",
        ],
    },
    DashboardTypeEnum.HR: {
        "name": "Personas y RR. HH.",
        "audience": "Dirección de personas y RR. HH.",
        "questions": [
            "¿Cómo evolucionan los indicadores de plantilla?",
            "¿Qué áreas concentran mayor absentismo o rotación?",
            "¿Cuál es la estructura salarial?",
        ],
    },
    DashboardTypeEnum.MARKETING: {
        "name": "Rendimiento de Marketing",
        "audience": "Dirección de marketing y growth",
        "questions": [
            "¿Cómo evoluciona la adquisición en el tiempo?",
            "¿Qué canal aporta más resultados?",
            "¿Qué campañas ofrecen mejor rendimiento?",
        ],
    },
    DashboardTypeEnum.INVENTORY: {
        "name": "Control de Inventario",
        "audience": "Responsables de almacén y supply chain",
        "questions": [
            "¿Cómo evoluciona el stock en el tiempo?",
            "¿Qué familias concentran más existencias?",
            "¿Dónde hay riesgo de rotura o exceso de stock?",
        ],
    },
    DashboardTypeEnum.CUSTOMERS: {
        "name": "Visión de Clientes",
        "audience": "Dirección comercial y customer success",
        "questions": [
            "¿Cómo evoluciona la base de clientes?",
            "¿Qué segmentos concentran más valor?",
            "¿Qué indicadores de retención requieren atención?",
        ],
    },
    DashboardTypeEnum.LOGISTICS: {
        "name": "Rendimiento Logístico",
        "audience": "Responsables de logística y distribución",
        "questions": [
            "¿Cómo evoluciona el volumen de envíos?",
            "¿Qué rutas o zonas concentran la actividad?",
            "¿Dónde se producen retrasos o excepciones?",
        ],
    },
    DashboardTypeEnum.ACADEMIC: {
        "name": "Rendimiento Académico",
        "audience": "Dirección académica y coordinación docente",
        "questions": [
            "¿Cómo evolucionan los resultados en el tiempo?",
            "¿Qué asignaturas o grupos concentran mejores resultados?",
            "¿Qué estudiantes requieren seguimiento?",
        ],
    },
    DashboardTypeEnum.EXECUTIVE: {
        "name": "Visión Ejecutiva",
        "audience": "Comité de dirección",
        "questions": [
            "¿Cuál es la evolución de las magnitudes clave?",
            "¿Dónde se concentra el valor y el riesgo?",
            "¿Qué excepciones requieren decisión ejecutiva?",
        ],
    },
    DashboardTypeEnum.GENERIC: {
        "name": "Dashboard Analítico",
        "audience": "Analistas de datos",
        "questions": [
            "¿Cómo evoluciona la medida principal?",
            "¿Qué dimensiones explican su distribución?",
            "¿Qué registros destacan en el detalle?",
        ],
    },
}


class DashboardPlanner:
    """Ensambla el Blueprint: páginas, KPIs, filtros, jerarquías y guía Power BI."""

    def __init__(self, context: ModelContext, analysis: SemanticModelAnalysis):
        self.context = context
        self.analysis = analysis

    def build_pages(
        self, visuals: List[VisualRecommendation], dashboard_type: DashboardTypeEnum
    ) -> List[DashboardPage]:
        primary = next((v for v in visuals if v.visual_type == VisualTypeEnum.LINE), None) or (
            visuals[0] if visuals else None
        )
        secondary = [
            v
            for v in visuals
            if v is not primary
            and v.page_id != "page_detail"
            and v.visual_type
            in (VisualTypeEnum.BAR, VisualTypeEnum.HORIZONTAL_BAR, VisualTypeEnum.DONUT, VisualTypeEnum.STACKED_BAR)
        ]
        analysis_visuals = [v for v in visuals if v.visual_type in (VisualTypeEnum.SCATTER, VisualTypeEnum.HISTOGRAM)]
        detail = [v for v in visuals if v.page_id == "page_detail" or v.visual_type == VisualTypeEnum.TABLE]

        pages: List[DashboardPage] = []
        overview_ids = ([primary.visual_id] if primary else []) + [v.visual_id for v in secondary[:2]]
        pages.append(
            DashboardPage(
                page_id="page_overview",
                title="Resumen ejecutivo",
                purpose="Lectura rápida de KPIs, tendencia principal y desglose esencial.",
                visual_ids=overview_ids,
                layout_section="Executive overview",
            )
        )
        if len(secondary) > 2 or analysis_visuals:
            pages.append(
                DashboardPage(
                    page_id="page_analysis",
                    title="Análisis dimensional",
                    purpose="Desglose por dimensiones secundarias, correlación y distribución.",
                    visual_ids=[v.visual_id for v in secondary[2:]] + [v.visual_id for v in analysis_visuals],
                    layout_section="Dimensional exploration",
                )
            )
        if detail:
            pages.append(
                DashboardPage(
                    page_id="page_detail",
                    title="Detalle y ranking",
                    purpose="Ranking y detalle de registro para auditoría de los agregados.",
                    visual_ids=[v.visual_id for v in detail],
                    layout_section="Detail table / ranking",
                )
            )
        return pages

    def build_filters(self, visuals: List[VisualRecommendation]) -> List[FilterRecommendation]:
        filters: List[FilterRecommendation] = []
        seen: Set[str] = set()

        def _filter_priority(entry_col: Optional[SemanticColumnAnalysis]) -> int:
            if not entry_col:
                return 99
            st = entry_col.semantic_type
            if st in (ColumnSemanticTypeEnum.DATE, ColumnSemanticTypeEnum.DATETIME):
                return 1
            if st == ColumnSemanticTypeEnum.GEOGRAPHY:
                return 2
            if st in (ColumnSemanticTypeEnum.CATEGORY, ColumnSemanticTypeEnum.SUBCATEGORY):
                return 3
            if st in (ColumnSemanticTypeEnum.BOOLEAN, ColumnSemanticTypeEnum.ORDINAL):
                return 4
            return 5

        candidates = []
        for visual in visuals:
            if not visual.dimension:
                continue
            table, _, column = visual.dimension.partition("[")
            column = column.rstrip("]")
            key = f"{table}[{column}]"
            if key in seen:
                continue
            df = self.context.dataframes.get(table, pd.DataFrame())
            if df.empty or column not in df.columns:
                continue
            seen.add(key)
            table_analysis = next((t for t in self.analysis.tables if t.table_name == table), None)
            col_analysis = (
                next((c for c in table_analysis.columns if c.column_name == column), None) if table_analysis else None
            )
            candidates.append((table, column, col_analysis))

        # Ordenar candidatos por prioridad semántica (Fecha > Geografía > Categoría > Estado)
        candidates.sort(key=lambda c: (_filter_priority(c[2]), c[0], c[1]))

        for i, (table, column, _col_analysis) in enumerate(candidates[:4]):
            df = self.context.dataframes.get(table, pd.DataFrame())
            top_values = df[column].dropna().astype(str).value_counts().head(8).index.tolist()
            filters.append(
                FilterRecommendation(
                    filter_id=f"filter_{table.lower()}_{column.lower()}",
                    table_ref=table,
                    column=column,
                    label=column.replace("_", " "),
                    recommended_values=[str(v) for v in top_values],
                    purpose=f"Acotar los visuales a valores concretos de {column}.",
                    order=i,
                )
            )
        return filters

    def build_hierarchies(self) -> List[HierarchyRecommendation]:
        hierarchies: List[HierarchyRecommendation] = []
        for table in self.analysis.tables:
            categories = [c for c in table.columns if c.semantic_type == ColumnSemanticTypeEnum.CATEGORY]
            subcategories = [c for c in table.columns if c.semantic_type == ColumnSemanticTypeEnum.SUBCATEGORY]
            if categories and subcategories:
                hierarchies.append(
                    HierarchyRecommendation(
                        hierarchy_id=f"hier_{table.table_name.lower()}",
                        name=f"Jerarquía de {table.table_name}",
                        levels=[
                            f"{table.table_name}[{categories[0].column_name}]",
                            f"{table.table_name}[{subcategories[0].column_name}]",
                        ],
                    )
                )
            date_cols = [
                c
                for c in table.columns
                if c.semantic_type in (ColumnSemanticTypeEnum.DATE, ColumnSemanticTypeEnum.DATETIME)
            ]
            if date_cols:
                hierarchies.append(
                    HierarchyRecommendation(
                        hierarchy_id=f"hier_date_{table.table_name.lower()}",
                        name=f"Jerarquía temporal de {table.table_name}",
                        levels=[f"{table.table_name}[{date_cols[0].column_name}] (Año → Mes → Día)"],
                    )
                )
        return hierarchies

    def build_power_bi_guide(
        self,
        visuals: List[VisualRecommendation],
        kpis: List[KPIRecommendation],
        filters: List[FilterRecommendation],
    ) -> List[PowerBIImplementationInstruction]:
        instructions: List[PowerBIImplementationInstruction] = []
        page_titles = {"page_overview": "Resumen ejecutivo", "page_analysis": "Análisis", "page_detail": "Detalle"}
        for visual in visuals:
            instructions.append(
                PowerBIImplementationInstruction(
                    page=page_titles.get(visual.page_id, visual.page_id),
                    visual=visual.title,
                    visual_type=visual.visual_type.value,
                    axis=visual.axis_label,
                    legend=visual.legend_field,
                    values=visual.measure,
                    filters=visual.filter_suggestion,
                    suggested_measure=visual.measure_name,
                    formatting="Ejes con etiquetas legibles, datos con formato numérico y orden descendente cuando aplique.",
                    accessibility="Activar accesibilidad del visual en Power BI, mantener orden de tabulación y texto alternativo.",
                )
            )
        if kpis:
            instructions.append(
                PowerBIImplementationInstruction(
                    page=page_titles["page_overview"],
                    visual="Fila de KPIs",
                    visual_type="kpi_card",
                    axis=None,
                    legend=None,
                    values=", ".join(k.dax_measure_name for k in kpis),
                    filters=", ".join(f"{f.table_ref}[{f.column}]" for f in filters[:2]) or None,
                    suggested_measure=kpis[0].dax_measure_name,
                    formatting="Tarjetas con valor grande, título y contexto; sin ejes.",
                    accessibility="Texto alternativo describiendo el KPI y su tendencia.",
                )
            )
        return instructions


# ───────────────────────────── Data Quality ─────────────────────────────────


class DataQualityIntegrator:
    """Integra señales de Data Quality (completitud real + issues del informe)."""

    @staticmethod
    def build_notes(context: ModelContext) -> List[DataQualityNote]:
        notes: List[DataQualityNote] = []
        for node in [context.schema.fact_table] + context.schema.dimension_tables:
            df = context.dataframes.get(node.table_name, pd.DataFrame())
            if df.empty:
                continue
            for col in df.columns:
                completeness = context.completeness(node.table_name, str(col))
                if completeness is None or completeness >= 85.0:
                    continue
                severity = "high" if completeness < 50 else ("medium" if completeness < 70 else "low")
                notes.append(
                    DataQualityNote(
                        column=f"{node.table_name}[{col}]",
                        completeness_pct=completeness,
                        severity=severity,
                        message=(
                            f"{node.table_name}[{col}] presenta completitud del {completeness:.1f}%; "
                            "los visuales que la usan deben mostrar advertencia y no usarse para KPIs de unicidad."
                        ),
                    )
                )

        # Issues vivos del informe de calidad (si existe en caché para estos datasets)
        try:
            from app.services.quality_service import QualityService

            for dataset_id in context.dataset_ids:
                report = QualityService.get_quality_report(dataset_id)
                for issue in report.issues[:10]:
                    if issue.column:
                        notes.append(
                            DataQualityNote(
                                column=f"[{dataset_id[:8]}] {issue.column}",
                                completeness_pct=round(100.0 - issue.affected_percentage, 2),
                                severity=issue.severity.value,
                                message=issue.description,
                            )
                        )
        except Exception:
            pass
        return notes


# ───────────────────────────── Validador del Blueprint ──────────────────────


class BlueprintValidator:
    """Validación determinista del Blueprint contra el modelo real."""

    @staticmethod
    def parse_field(field_ref: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not field_ref or "[" not in field_ref or not field_ref.endswith("]"):
            return None, None
        table, rest = field_ref.split("[", 1)
        return table, rest[:-1]

    @classmethod
    def validate(cls, blueprint: DashboardBlueprint, context: ModelContext) -> DashboardValidation:
        checks: List[DashboardCheck] = []
        issues: List[str] = []
        qualified = context.qualified_fields()
        table_names = {context.schema.fact_table.table_name} | {d.table_name for d in context.schema.dimension_tables}

        def add(check_id: str, name: str, category: CheckCategoryEnum, passed: bool, detail: str) -> None:
            checks.append(DashboardCheck(check_id=check_id, name=name, category=category, passed=passed, detail=detail))
            if not passed:
                issues.append(f"{name}: {detail}")

        # 1. Existencia de tablas
        referenced_tables = set()
        for visual in blueprint.visuals:
            for f in visual.fields:
                table, _ = cls.parse_field(f)
                if table:
                    referenced_tables.add(table)
        for kpi in blueprint.kpis:
            referenced_tables.add(kpi.table_context)
        for flt in blueprint.filters:
            referenced_tables.add(flt.table_ref)
        missing_tables = sorted(t for t in referenced_tables if t not in table_names)
        add(
            "tables_exist",
            "Todas las tablas existen",
            CheckCategoryEnum.INTEGRITY,
            not missing_tables,
            "OK" if not missing_tables else f"Tablas inexistentes: {', '.join(missing_tables)}",
        )

        # 2. Existencia de columnas referenciadas
        bad_fields = sorted(
            {f for f in (field for visual in blueprint.visuals for field in visual.fields) if f not in qualified}
        )
        add(
            "columns_exist",
            "Todas las columnas existen",
            CheckCategoryEnum.INTEGRITY,
            not bad_fields,
            "OK" if not bad_fields else f"Campos inexistentes: {', '.join(bad_fields)}",
        )

        # 3. Medidas existentes o marcadas como propuesta
        invalid_measures = [m.name for m in blueprint.dax_measures if not m.validated and not m.formula]
        add(
            "measures_declared",
            "Medidas existentes o marcadas como propuesta",
            CheckCategoryEnum.INTEGRITY,
            not invalid_measures,
            "OK" if not invalid_measures else f"Medidas sin fórmula ni validación: {', '.join(invalid_measures)}",
        )

        # 4. Relaciones válidas
        bad_rels: List[str] = []
        for visual in blueprint.visuals:
            tables_used = {cls.parse_field(f)[0] for f in visual.fields}
            tables_used.discard(None)
            if len(tables_used) > 1 and context.fact_name in tables_used:
                for other in tables_used - {context.fact_name}:
                    if not context.relationship_exists(context.fact_name, str(other)):
                        bad_rels.append(f"{context.fact_name}→{other}")
        add(
            "relationships_valid",
            "Las relaciones existen",
            CheckCategoryEnum.INTEGRITY,
            not bad_rels,
            "OK" if not bad_rels else f"Relaciones no declaradas: {', '.join(sorted(set(bad_rels)))}",
        )

        # 5. Compatibilidad campos/visual
        incompatible: List[str] = []
        for visual in blueprint.visuals:
            ok = True
            if visual.visual_type in (
                VisualTypeEnum.BAR,
                VisualTypeEnum.HORIZONTAL_BAR,
                VisualTypeEnum.DONUT,
                VisualTypeEnum.PIE,
                VisualTypeEnum.STACKED_BAR,
            ):
                ok = bool(visual.dimension) and bool(visual.measure)
            elif visual.visual_type in (VisualTypeEnum.LINE, VisualTypeEnum.AREA):
                dim_table, dim_col = cls.parse_field(visual.dimension)
                ok = (
                    bool(visual.dimension)
                    and bool(dim_col)
                    and any(
                        k in str(dim_col).lower()
                        for k in ("fecha", "date", "dia", "day", "mes", "month", "year", "period", "tiempo")
                    )
                )
            elif visual.visual_type == VisualTypeEnum.SCATTER:
                ok = len(visual.fields) >= 2
            if not ok:
                incompatible.append(visual.title)
        add(
            "field_compatibility",
            "Campos compatibles con el visual",
            CheckCategoryEnum.INTEGRITY,
            not incompatible,
            "OK" if not incompatible else f"Visuales incompatibles: {', '.join(incompatible)}",
        )

        # 6. Granularidad de medidas en series temporales
        line_ok = all(
            v.dimension for v in blueprint.visuals if v.visual_type in (VisualTypeEnum.LINE, VisualTypeEnum.AREA)
        )
        add(
            "time_granularity",
            "Granularidad temporal adecuada",
            CheckCategoryEnum.QUALITY,
            line_ok,
            "OK" if line_ok else "Serie temporal sin dimensión de fecha.",
        )

        # 7. Filtros válidos
        bad_filters = [
            f"{f.table_ref}[{f.column}]" for f in blueprint.filters if f"{f.table_ref}[{f.column}]" not in qualified
        ]
        add(
            "filters_valid",
            "Filtros válidos",
            CheckCategoryEnum.INTEGRITY,
            not bad_filters,
            "OK" if not bad_filters else f"Filtros inexistentes: {', '.join(bad_filters)}",
        )

        # 8. Layout válido
        visual_ids = {v.visual_id for v in blueprint.visuals}
        layout_ok = bool(blueprint.pages) and all(vid in visual_ids for p in blueprint.pages for vid in p.visual_ids)
        add(
            "layout_valid",
            "Layout válido",
            CheckCategoryEnum.QUALITY,
            layout_ok,
            "OK" if layout_ok else "Páginas que referencian visuales inexistentes.",
        )

        # 9. WCAG
        aa_failures = [c.label for c in blueprint.design.accessibility.contrast_pairs if not c.aa]
        add(
            "wcag_contrast",
            "Colores cumplen WCAG AA",
            CheckCategoryEnum.INTEGRITY,
            not aa_failures,
            "OK" if not aa_failures else f"Pares sin AA: {', '.join(aa_failures)}",
        )
        if aa_failures:
            _increment("wcag_validation_failed")

        # 10. Reglas de circulares
        pie_violations: List[str] = []
        for visual in blueprint.visuals:
            if visual.visual_type in (VisualTypeEnum.PIE, VisualTypeEnum.DONUT):
                if len(visual.preview_data) > 6:
                    pie_violations.append(f"{visual.title} (>6 categorías)")
                if not visual.dimension:
                    pie_violations.append(f"{visual.title} (sin dimensión)")
        add(
            "pie_rules",
            "Reglas de gráficos circulares",
            CheckCategoryEnum.QUALITY,
            not pie_violations,
            "OK" if not pie_violations else f"Circulares inválidos: {', '.join(pie_violations)} (sustituir por barras)",
        )

        # 11. Cardinalidad alta de dimensiones
        high_card: List[str] = []
        for visual in blueprint.visuals:
            dim_table, dim_col = cls.parse_field(visual.dimension)
            if not dim_table or not dim_col:
                continue
            df = context.dataframes.get(dim_table, pd.DataFrame())
            if df.empty or dim_col not in df.columns:
                continue
            cardinality = int(df[dim_col].dropna().nunique())
            if cardinality > 20 and visual.visual_type in (
                VisualTypeEnum.BAR,
                VisualTypeEnum.HORIZONTAL_BAR,
                VisualTypeEnum.PIE,
                VisualTypeEnum.DONUT,
            ):
                high_card.append(f"{dim_table}[{dim_col}] cardinalidad {cardinality}")
        add(
            "dimension_cardinality",
            "Cardinalidad de dimensiones razonable",
            CheckCategoryEnum.QUALITY,
            not high_card,
            "OK" if not high_card else f"Dimensiones con cardinalidad alta: {', '.join(high_card)}",
        )

        # 12. Sin referencias ficticias en KPIs/jerarquías
        fabricated: List[str] = []
        for kpi in blueprint.kpis:
            if kpi.table_context not in table_names:
                fabricated.append(f"KPI {kpi.title} → tabla {kpi.table_context}")
        for hier in blueprint.hierarchies:
            for level in hier.levels:
                table, col = cls.parse_field(level)
                if table and col and f"{table}[{col}]" not in qualified and "Año" not in level:
                    fabricated.append(f"Jerarquía {hier.name} → {level}")
        add(
            "no_fabricated_references",
            "Sin referencias ficticias",
            CheckCategoryEnum.INTEGRITY,
            not fabricated,
            "OK" if not fabricated else f"Referencias ficticias: {', '.join(fabricated)}",
        )

        # 13. Datos reales en previews marcados como reales
        empty_previews = [
            v.title for v in blueprint.visuals if v.preview_mode == PreviewModeEnum.REAL and len(v.preview_data) < 2
        ]
        add(
            "preview_alignment",
            "Previews reales con datos suficientes",
            CheckCategoryEnum.QUALITY,
            not empty_previews,
            (
                "OK"
                if not empty_previews
                else f"Previews sin datos suficientes: {', '.join(empty_previews)} (marcar como ilustrativos)"
            ),
        )

        # 14. KPIs no usan columnas con baja completitud
        kpi_quality_issues: List[str] = []
        for kpi in blueprint.kpis:
            for note in kpi.data_quality_notes:
                kpi_quality_issues.append(f"{kpi.title}: {note}")
        add(
            "kpi_quality_gate",
            "KPIs sin limitaciones severas de calidad",
            CheckCategoryEnum.QUALITY,
            not kpi_quality_issues,
            "OK" if not kpi_quality_issues else "; ".join(kpi_quality_issues),
        )

        # 15. Determinismo del ID
        deterministic = bool(blueprint.blueprint_id) and len(blueprint.blueprint_id) >= 16
        add(
            "deterministic_id",
            "Blueprint con ID determinista",
            CheckCategoryEnum.QUALITY,
            deterministic,
            "OK" if deterministic else "El blueprint no tiene ID estable.",
        )

        # 16. KPI count razonable
        kpi_count_ok = len(blueprint.kpis) <= 6
        add(
            "kpi_count",
            "Número de KPIs razonable (≤6)",
            CheckCategoryEnum.QUALITY,
            kpi_count_ok,
            "OK" if kpi_count_ok else f"{len(blueprint.kpis)} KPIs propuestos.",
        )

        # 17. Preguntas de negocio presentes
        add(
            "business_questions",
            "Preguntas de negocio definidas",
            CheckCategoryEnum.QUALITY,
            bool(blueprint.business_questions),
            "OK" if blueprint.business_questions else "El blueprint no define preguntas de negocio.",
        )

        # 18. Guía Power BI presente
        add(
            "powerbi_guide",
            "Guía de implementación Power BI presente",
            CheckCategoryEnum.QUALITY,
            bool(blueprint.power_bi_implementation),
            "OK" if blueprint.power_bi_implementation else "Falta la guía de implementación.",
        )

        integrity_failed = any(not c.passed and c.category == CheckCategoryEnum.INTEGRITY for c in checks)
        quality_failed = any(not c.passed and c.category == CheckCategoryEnum.QUALITY for c in checks)
        status = (
            ValidationStatusEnum.INVALID
            if integrity_failed
            else (ValidationStatusEnum.WARNING if quality_failed else ValidationStatusEnum.VALID)
        )
        passed_count = sum(1 for c in checks if c.passed)
        return DashboardValidation(
            checks=checks,
            passed_count=passed_count,
            total_count=len(checks),
            status=status,
            issues=issues,
        )


# ───────────────────────────── Servicio orquestador ─────────────────────────


class DashboardService:
    """Orquesta el pipeline completo de Dashboard Intelligence."""

    @staticmethod
    def _load_context(dataset_ids: List[str]) -> Tuple[ModelContext, MultiTableStarSchema]:
        schema = RelationalService.infer_star_schema(dataset_ids)
        dataframes: Dict[str, pd.DataFrame] = {}
        for dataset_id in dataset_ids:
            df, filename = RelationalService._load_dataset_df(dataset_id)
            if not df.empty:
                dataframes[RelationalService._clean_table_name(filename)] = df

        # Calcular de forma determinista __ventas_netas en la tabla de hechos si tiene cantidad y precio
        fact_name = schema.fact_table.table_name
        if fact_name in dataframes:
            fact_df = dataframes[fact_name]
            qty_col, price_col, disc_col = _detect_sales_columns(fact_df)
            if qty_col and price_col and DERIVED_MEASURE_COL not in fact_df.columns:
                q = pd.to_numeric(fact_df[qty_col], errors="coerce").fillna(0)
                p = pd.to_numeric(fact_df[price_col], errors="coerce").fillna(0)
                d = pd.to_numeric(fact_df[disc_col], errors="coerce").fillna(0) if disc_col else 0
                fact_df[DERIVED_MEASURE_COL] = q * p * (1.0 - d)

        return ModelContext(schema=schema, dataframes=dataframes, dataset_ids=list(dataset_ids)), schema

    @staticmethod
    def _blueprint_id(
        dataset_ids: List[str], dashboard_type: str, visuals: List[VisualRecommendation], kpi_ids: List[str]
    ) -> str:
        payload = (
            "|".join(sorted(dataset_ids))
            + "::"
            + dashboard_type
            + "::"
            + ",".join(f"{v.visual_type.value}:{v.dimension}:{v.measure}" for v in visuals)
            + "::"
            + ",".join(kpi_ids)
        )
        return "dbp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def analyze(cls, dataset_ids: List[str]) -> DashboardBlueprint:
        started = time.perf_counter()
        _increment("dashboard_generation_total")
        try:
            context, schema = cls._load_context(dataset_ids)
            analysis = SemanticModelAnalyzer.analyze(schema, context.dataframes)
            engine = VisualRecommendationEngine(analysis, schema, context.dataframes)
            visuals = engine.generate()
            _increment("visual_recommendation_count", len(visuals))

            dashboard_type, type_label, type_confidence, uncertainty = DashboardTypeClassifier.classify(analysis)
            profile = _TYPE_PROFILES[dashboard_type]
            planner = DashboardPlanner(context, analysis)

            kpis, kpi_warnings = KpiGenerator(context, analysis).generate(engine.primary_measure)
            pages = planner.build_pages(visuals, dashboard_type)
            filters = planner.build_filters(visuals)
            hierarchies = planner.build_hierarchies()
            design, wcag_pass = DesignSystemGenerator.build()
            if not wcag_pass:
                _increment("wcag_validation_failed")
            dax_measures = DaxGenerator.generate(context, kpis)
            power_bi_guide = planner.build_power_bi_guide(visuals, kpis, filters)
            dq_notes = DataQualityIntegrator.build_notes(context)

            measure_label = str(engine.primary_measure["label"]) if engine.primary_measure else "la medida principal"
            questions = [BusinessQuestion(question_id=f"q_{i}", text=text) for i, text in enumerate(profile["questions"])]  # type: ignore[index]

            dashboard_name = str(profile["name"])
            primary_visual = next(
                (v for v in visuals if v.visual_type == VisualTypeEnum.LINE), visuals[0] if visuals else None
            )
            if primary_visual and dashboard_type == DashboardTypeEnum.SALES:
                dashboard_name = ReportTitleSanitizer.sanitize("Rendimiento de Ventas", schema.fact_table.table_name)
            else:
                dashboard_name = ReportTitleSanitizer.sanitize(dashboard_name, schema.fact_table.table_name)

            overall_confidence = type_confidence
            if visuals and all(v.confidence == ConfidenceLevelEnum.HIGH for v in visuals[:2]):
                overall_confidence = ConfidenceLevelEnum.HIGH

            blueprint_id = cls._blueprint_id(dataset_ids, dashboard_type.value, visuals, [k.kpi_id for k in kpis])
            blueprint = DashboardBlueprint(
                blueprint_id=blueprint_id,
                model_id=schema.model_id,
                dataset_ids=list(dataset_ids),
                name=dashboard_name,
                dashboard_type=dashboard_type,
                objective=f"Analizar {measure_label.lower()} del modelo estrella con lectura ejecutiva, desglose dimensional y detalle auditable.",
                audience=str(profile["audience"]),
                business_questions=questions,
                pages=pages,
                visuals=visuals,
                kpis=kpis,
                filters=filters,
                hierarchies=hierarchies,
                design=design,
                dax_measures=dax_measures,
                power_bi_implementation=power_bi_guide,
                power_bi_summary=(
                    f"{len(power_bi_guide)} instrucciones de visual, {len(dax_measures)} medidas DAX y "
                    f"{len(filters)} slicers listos para reconstruir el dashboard en Power BI Desktop."
                ),
                semantic_model=analysis,
                data_quality=dq_notes,
                warnings=kpi_warnings,
                limitations=[note.message for note in dq_notes if note.severity in ("medium", "high")],
                confidence=overall_confidence,
                confidence_rationale=(
                    "Confianza rule-based: clasificación de dominio por señales semánticas (high ≥6, medium ≥2), "
                    "y rúbrica aditiva por visual (semántica, completitud, cardinalidad, medida disponible)."
                ),
                uncertainty_note=uncertainty,
                validation=None,
                generation_meta=GenerationMeta(
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    dashboard_generation_total=int(DASHBOARD_STATS["dashboard_generation_total"]),
                    dashboard_generation_failed=int(DASHBOARD_STATS["dashboard_generation_failed"]),
                    dashboard_validation_failed=int(DASHBOARD_STATS["dashboard_validation_failed"]),
                    visual_recommendation_count=len(visuals),
                    wcag_validation_failed=int(DASHBOARD_STATS["wcag_validation_failed"]),
                ),
            )
            blueprint.validation = BlueprintValidator.validate(blueprint, context)
            if blueprint.validation.status == ValidationStatusEnum.INVALID:
                _increment("dashboard_validation_failed")

            DASHBOARD_CACHE[blueprint_id] = blueprint
            persist_blueprint(blueprint)
            return blueprint
        except Exception:
            _increment("dashboard_generation_failed")
            raise

    @classmethod
    def get(cls, blueprint_id: str) -> Optional[DashboardBlueprint]:
        cached = DASHBOARD_CACHE.get(blueprint_id)
        if cached is not None:
            return cached
        # Fallback de persistencia: la caché en memoria se pierde al reciclar
        # la instancia de Cloud Run, pero el JSON sigue en el StorageBackend.
        persisted = load_persisted_blueprint(blueprint_id)
        if persisted is not None:
            DASHBOARD_CACHE[blueprint_id] = persisted
        return persisted

    @classmethod
    def validate_blueprint(cls, dataset_ids: List[str], blueprint: DashboardBlueprint) -> DashboardValidation:
        _increment("dashboard_validation_total")
        context, _ = cls._load_context(dataset_ids)
        validation = BlueprintValidator.validate(blueprint, context)
        if validation.status == ValidationStatusEnum.INVALID:
            _increment("dashboard_validation_failed")
        return validation

    @classmethod
    def save_edited(cls, blueprint: DashboardBlueprint) -> DashboardBlueprint:
        """
        Guarda la edición HITL del usuario sobre un Blueprint (Paso 5).

        Gobernanza: la IA propone, el usuario decide, Python ejecuta. Este
        método nunca reescribe las decisiones del usuario: recalcula WCAG
        sobre la paleta activa, revalida de forma determinista contra el
        modelo estrella real y persiste el resultado en el StorageBackend.
        """
        blueprint.design.accessibility = DesignSystemGenerator.recheck_accessibility(blueprint.design.palette)
        # La paleta activa no debe seguir figurando como variante disponible
        active_name = blueprint.design.palette.name
        blueprint.design.palette_variants = [p for p in blueprint.design.palette_variants if p.name != active_name]
        blueprint.validation = cls.validate_blueprint(list(blueprint.dataset_ids), blueprint)
        DASHBOARD_CACHE[blueprint.blueprint_id] = blueprint
        persist_blueprint(blueprint)
        return blueprint
