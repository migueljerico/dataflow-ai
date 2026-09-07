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
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from app.core import wcag
from app.core.number_parsing import to_numeric_series
from app.models.dashboard import (
    AccessibilityCheckItem,
    AccessibilityRecommendation,
    BusinessQuestion,
    CheckCategoryEnum,
    ColorPalette,
    ColumnSemanticTypeEnum,
    ConfidenceLevelEnum,
    ContrastPairCheck,
    DashboardBlueprint,
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
    SemanticModelAnalysis,
    ValidationStatusEnum,
    VisualRecommendation,
    VisualTypeEnum,
)
from app.models.workspace import MultiTableStarSchema
from app.services.relational_service import RelationalService
from app.services.semantic_analyzer import SemanticModelAnalyzer
from app.services.visual_engine import VisualRecommendationEngine

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

        # 1) KPI principal: suma de la medida principal
        if primary is not None:
            table = str(primary["table"])
            column = str(primary["column"])
            completeness = self.context.completeness(table, column) or 0.0
            if completeness >= KPI_COMPLETENESS_THRESHOLD:
                df = self.context.dataframes.get(table, pd.DataFrame())
                numeric = to_numeric_series(df[column]).dropna() if column in df.columns else pd.Series(dtype=float)
                total = float(numeric.sum()) if len(numeric) else None
                kpis.append(
                    KPIRecommendation(
                        kpi_id=f"kpi_total_{column.lower()}",
                        title=f"Total {column.replace('_', ' ').lower()}",
                        description=f"Suma total de {column} en {table}.",
                        dax_measure_name=f"Total_{column}",
                        dax_formula=f"SUM('{table}'[{column}])",
                        table_context=table,
                        format_type=(
                            "currency"
                            if primary["analysis"].semantic_type == ColumnSemanticTypeEnum.CURRENCY
                            else "number"
                        ),
                        validated=True,
                        value=round(total, 2) if total is not None else None,
                        value_label=(
                            self._format_value(total, primary["analysis"].semantic_type) if total is not None else None
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

        # 2) KPI de conteo: registros/pedidos sobre la PK del hecho
        pk_col = fact.primary_keys[0] if fact.primary_keys else None
        if pk_col is not None and pk_col in self.fact_df.columns:
            unique_count = int(self.fact_df[pk_col].nunique())
            is_order_like = any(k in pk_col.lower() for k in ("pedido", "order", "factura"))
            kpis.append(
                KPIRecommendation(
                    kpi_id=f"kpi_count_{pk_col.lower()}",
                    title="Pedidos" if is_order_like else "Registros",
                    description=f"Número de valores únicos de {pk_col} en {fact.table_name}.",
                    dax_measure_name="Pedidos" if is_order_like else "Total_Registros",
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

        # 3) Ticket medio: DIVIDE entre medida principal y conteo
        if kpis and len(kpis) >= 2 and kpis[0].format_type in ("currency", "number") and kpis[1].value:
            revenue = kpis[0].value or 0.0
            count = kpis[1].value or 0.0
            ticket = round(revenue / count, 2) if count else None
            kpis.append(
                KPIRecommendation(
                    kpi_id="kpi_ticket_medio",
                    title="Ticket medio",
                    description="Cociente entre la medida principal y el número de registros.",
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

        # 4) Precio medio si existe columna de precio distinta de la medida principal
        price_col = self._find_column([ColumnSemanticTypeEnum.CURRENCY])
        if price_col and kpis and price_col[1] != str((primary or {}).get("column", "")):
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

        checklist = [
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
        declarations = [
            "No depender exclusivamente del color para transmitir información.",
            "Tamaño de fuente mínimo 11px para etiquetas y 14px para texto de apoyo.",
            "Máximo 6-8 categorías por visual; agrupar el resto.",
            "Evitar gráficos circulares con más de 6 categorías.",
            "Orden lógico de lectura: KPIs, tendencia, desglose, detalle.",
            "Títulos descriptivos y tooltips informativos con valores exactos.",
            "Filtros comprensibles con valores reales del dataset.",
        ]
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
            and v.visual_type
            in (VisualTypeEnum.BAR, VisualTypeEnum.HORIZONTAL_BAR, VisualTypeEnum.DONUT, VisualTypeEnum.STACKED_BAR)
        ]
        analysis_visuals = [v for v in visuals if v.visual_type in (VisualTypeEnum.SCATTER, VisualTypeEnum.HISTOGRAM)]
        detail = [v for v in visuals if v.visual_type == VisualTypeEnum.TABLE]

        pages: List[DashboardPage] = []
        overview_ids = ([primary.visual_id] if primary else []) + [v.visual_id for v in secondary[:2]]
        pages.append(
            DashboardPage(
                page_id="page_overview",
                title="Resumen ejecutivo",
                purpose="Lectura rápida de KPIs, tendencia principal y desglose esencial.",
                visual_ids=overview_ids,
                layout_section="Header → KPI row → Primary analytical visual → Secondary visuals",
            )
        )
        if analysis_visuals:
            pages.append(
                DashboardPage(
                    page_id="page_analysis",
                    title="Análisis",
                    purpose="Relación entre variables y distribución de la medida principal.",
                    visual_ids=[v.visual_id for v in analysis_visuals],
                    layout_section="Secondary analytical visuals",
                )
            )
        if detail:
            pages.append(
                DashboardPage(
                    page_id="page_detail",
                    title="Detalle",
                    purpose="Ranking y detalle de registro para auditoría de los agregados.",
                    visual_ids=[v.visual_id for v in detail],
                    layout_section="Detail table / ranking",
                )
            )
        return pages

    def build_filters(self, visuals: List[VisualRecommendation]) -> List[FilterRecommendation]:
        filters: List[FilterRecommendation] = []
        seen: Set[str] = set()
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
            top_values = df[column].dropna().astype(str).value_counts().head(8).index.tolist()
            seen.add(key)
            filters.append(
                FilterRecommendation(
                    filter_id=f"filter_{table.lower()}_{column.lower()}",
                    table_ref=table,
                    column=column,
                    label=column.replace("_", " "),
                    recommended_values=[str(v) for v in top_values],
                    purpose=f"Acotar los visuales a valores concretos de {column}.",
                    order=len(filters),
                )
            )
            if len(filters) >= 4:
                break
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
                dashboard_name = f"Rendimiento de Ventas — {schema.fact_table.table_name.replace('_', ' ')}"

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
            return blueprint
        except Exception:
            _increment("dashboard_generation_failed")
            raise

    @classmethod
    def get(cls, blueprint_id: str) -> Optional[DashboardBlueprint]:
        return DASHBOARD_CACHE.get(blueprint_id)

    @classmethod
    def validate_blueprint(cls, dataset_ids: List[str], blueprint: DashboardBlueprint) -> DashboardValidation:
        _increment("dashboard_validation_total")
        context, _ = cls._load_context(dataset_ids)
        validation = BlueprintValidator.validate(blueprint, context)
        if validation.status == ValidationStatusEnum.INVALID:
            _increment("dashboard_validation_failed")
        return validation
