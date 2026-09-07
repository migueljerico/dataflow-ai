"""
Modelos del módulo Dashboard Intelligence / Dashboard Preview.

El DashboardBlueprint es una especificación estructurada, validable y
reproducible del dashboard recomendado a partir del esquema estrella. Los
datos de previsualización (preview_data) se calculan de forma determinista en
Python/Pandas y nunca son inventados por un LLM.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardTypeEnum(str, Enum):
    SALES = "sales"
    FINANCE = "finance"
    OPERATIONS = "operations"
    HR = "hr"
    MARKETING = "marketing"
    INVENTORY = "inventory"
    CUSTOMERS = "customers"
    LOGISTICS = "logistics"
    ACADEMIC = "academic"
    EXECUTIVE = "executive"
    GENERIC = "generic"


class VisualTypeEnum(str, Enum):
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    LINE = "line"
    AREA = "area"
    STACKED_BAR = "stacked_bar"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    TABLE = "table"
    KPI_CARD = "kpi_card"


class ConfidenceLevelEnum(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TableSemanticRoleEnum(str, Enum):
    FACT = "fact"
    DIMENSION = "dimension"
    DATE = "date"
    CUSTOMER = "customer"
    PRODUCT = "product"
    EMPLOYEE = "employee"
    STORE = "store"
    REGION = "region"
    BRIDGE = "bridge"
    UNKNOWN = "unknown"


class ColumnSemanticTypeEnum(str, Enum):
    DATE = "date"
    DATETIME = "datetime"
    IDENTIFIER = "identifier"
    MEASURE = "measure"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    QUANTITY = "quantity"
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"
    GEOGRAPHY = "geography"
    NAME = "name"
    EMAIL = "email"
    BOOLEAN = "boolean"
    TEXT = "text"
    ORDINAL = "ordinal"


class ValidationStatusEnum(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


class PreviewModeEnum(str, Enum):
    REAL = "real"
    ILLUSTRATIVE = "illustrative"


class CheckCategoryEnum(str, Enum):
    INTEGRITY = "integrity"
    QUALITY = "quality"


# ────────────────────────── Análisis semántico ───────────────────────────────


class SemanticColumnAnalysis(BaseModel):
    table_name: str = Field(..., description="Tabla a la que pertenece la columna")
    column_name: str = Field(..., description="Nombre de la columna")
    semantic_type: ColumnSemanticTypeEnum = Field(..., description="Clasificación semántica de la columna")
    cardinality: int = Field(..., description="Número de valores distintos (no nulos)")
    null_percentage: float = Field(..., description="Porcentaje de valores nulos")
    completeness_pct: float = Field(..., description="Completitud 100 - null_percentage")
    inferred_from: str = Field(..., description="Señales usadas: name, type, cardinality, values, relationship")
    is_heuristic: bool = Field(..., description="True si la clasificación es heurística y no categórica")


class SemanticTableAnalysis(BaseModel):
    table_id: str = Field(..., description="ID del dataset origen")
    table_name: str = Field(..., description="Nombre canónico de la tabla en el modelo")
    star_role: str = Field(..., description="Rol en el esquema estrella (fact, dimension, ...)")
    semantic_role: TableSemanticRoleEnum = Field(..., description="Rol semántico de negocio inferido")
    row_count: int = Field(..., description="Filas de la tabla")
    columns: List[SemanticColumnAnalysis] = Field(default_factory=list, description="Análisis semántico por columna")
    heuristic_note: Optional[str] = Field(None, description="Nota cuando la clasificación es heurística")


class SemanticModelAnalysis(BaseModel):
    model_id: str = Field(..., description="ID del modelo estrella analizado")
    tables: List[SemanticTableAnalysis] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(
        default_factory=list, description="Notas sobre señales insuficientes o ambiguas"
    )


# ────────────────────────── Recomendaciones del Blueprint ────────────────────


class KPIRecommendation(BaseModel):
    kpi_id: str = Field(..., description="ID estable y determinista del KPI")
    title: str = Field(..., description="Título del KPI")
    description: str = Field(..., description="Qué mide y para qué sirve")
    dax_measure_name: str = Field(..., description="Nombre de la medida DAX asociada")
    dax_formula: str = Field(..., description="Fórmula DAX de la medida")
    table_context: str = Field(..., description="Tabla del modelo donde vive la medida")
    format_type: str = Field("number", description="Formato: currency, number, percentage, decimal")
    validated: bool = Field(..., description="True si la medida existe en el modelo real; False si es propuesta")
    value: Optional[float] = Field(None, description="Valor real calculado con los datos disponibles (si existe)")
    value_label: Optional[str] = Field(None, description="Valor formateado para presentación")
    confidence: ConfidenceLevelEnum = Field(..., description="Confianza rule-based de la recomendación")
    data_quality_notes: List[str] = Field(default_factory=list, description="Advertencias derivadas de Data Quality")
    order: int = Field(..., description="Posición en la fila de KPIs")


class PreviewDataPoint(BaseModel):
    label: str = Field(..., description="Etiqueta de la categoría, fecha o punto")
    value: float = Field(..., description="Valor principal")
    secondary_value: Optional[float] = Field(None, description="Valor secundario (segunda serie)")


class VisualRecommendation(BaseModel):
    visual_id: str = Field(..., description="ID estable y determinista del visual")
    title: str = Field(..., description="Título descriptivo del visual")
    visual_type: VisualTypeEnum = Field(..., description="Tipo de visualización recomendado")
    page_id: str = Field(..., description="Página del dashboard a la que pertenece")
    dimension: Optional[str] = Field(None, description="Campo de dimensión cualificado Tabla[Columna]")
    measure: Optional[str] = Field(None, description="Campo de medida cualificado Tabla[Columna]")
    measure_name: Optional[str] = Field(None, description="Nombre de la medida DAX sugerida")
    fields: List[str] = Field(default_factory=list, description="Todos los campos cualificados usados por el visual")
    axis_label: Optional[str] = Field(None, description="Etiqueta del eje (usado como X en Power BI)")
    legend_field: Optional[str] = Field(None, description="Campo de leyenda/serie opcional")
    filter_suggestion: Optional[str] = Field(None, description="Filtro sugerido (ej. DimDate[Year])")
    reason: str = Field(..., description="Justificación de la recomendación")
    confidence: ConfidenceLevelEnum = Field(..., description="Confianza rule-based (high/medium/low)")
    confidence_rationale: str = Field(..., description="Metodología objetiva que produce el nivel de confianza")
    alternative_types: List[VisualTypeEnum] = Field(
        default_factory=list, description="Alternativas compatibles pre-validadas para el usuario"
    )
    preview_data: List[PreviewDataPoint] = Field(default_factory=list, description="Datos reales agregados")
    preview_mode: PreviewModeEnum = Field(
        default=PreviewModeEnum.REAL, description="real=datos reales, illustrative=sin datos suficientes"
    )
    data_quality_notes: List[str] = Field(default_factory=list, description="Advertencias de Data Quality")
    accessibility_note: Optional[str] = Field(None, description="Recomendación de accesibilidad específica del visual")
    order: int = Field(..., description="Orden de lectura dentro de su página")


class BusinessQuestion(BaseModel):
    question_id: str = Field(..., description="ID de la pregunta de negocio")
    text: str = Field(..., description="Pregunta que el dashboard ayuda a responder")


class HierarchyRecommendation(BaseModel):
    hierarchy_id: str = Field(..., description="ID de la jerarquía")
    name: str = Field(..., description="Nombre de la jerarquía")
    levels: List[str] = Field(default_factory=list, description="Niveles cualificados del más agregado al más fino")


class FilterRecommendation(BaseModel):
    filter_id: str = Field(..., description="ID del filtro/slicer")
    table_ref: str = Field(..., description="Tabla 'DimX' del filtro")
    column: str = Field(..., description="Columna del filtro")
    label: str = Field(..., description="Etiqueta legible del slicer")
    recommended_values: List[str] = Field(
        default_factory=list, description="Valores recomendados (top valores reales, máx. 8)"
    )
    purpose: str = Field(..., description="Para qué sirve el filtro")
    order: int = Field(..., description="Posición en el panel de filtros")


class DashboardPage(BaseModel):
    page_id: str = Field(..., description="ID de la página")
    title: str = Field(..., description="Título de la página")
    purpose: str = Field(..., description="Objetivo analítico de la página")
    visual_ids: List[str] = Field(default_factory=list, description="IDs de los visuals en orden de lectura")
    layout_section: str = Field(
        ..., description="Sección del layout: KPI row, primary analytical, secondary, detail, filters"
    )


# ────────────────────────── Diseño y accesibilidad ───────────────────────────


class ColorPalette(BaseModel):
    name: str = Field(..., description="Nombre de la paleta")
    primary_color: str = Field(..., description="Color primario #RRGGBB")
    secondary_color: str = Field(..., description="Color secundario #RRGGBB")
    accent_color: str = Field(..., description="Color de acento #RRGGBB")
    background_color: str = Field(..., description="Color de fondo #RRGGBB")
    text_color: str = Field(..., description="Color de texto principal #RRGGBB")
    muted_text_color: str = Field(..., description="Color de texto atenuado #RRGGBB")
    positive_color: str = Field(..., description="Color semántico positivo #RRGGBB")
    negative_color: str = Field(..., description="Color semántico negativo #RRGGBB")
    warning_color: str = Field(..., description="Color semántico de aviso #RRGGBB")


class ContrastPairCheck(BaseModel):
    label: str = Field(..., description="Etiqueta legible del par evaluado")
    foreground: str = Field(..., description="Color frontal #RRGGBB")
    background: str = Field(..., description="Color de fondo #RRGGBB")
    contrast_ratio: float = Field(..., description="Ratio de contraste calculada")
    aa: bool = Field(..., description="Cumple WCAG AA")
    aaa: bool = Field(..., description="Cumple WCAG AAA")
    large_text: bool = Field(False, description="Evaluado como texto grande")


class AccessibilityCheckItem(BaseModel):
    label: str = Field(..., description="Ítem del checklist de accesibilidad")
    status: str = Field(..., description="pass o warning")
    detail: str = Field(..., description="Detalle o recomendación")


class AccessibilityRecommendation(BaseModel):
    contrast_pairs: List[ContrastPairCheck] = Field(default_factory=list, description="Pares evaluados matemáticamente")
    checklist: List[AccessibilityCheckItem] = Field(default_factory=list, description="Checklist de accesibilidad")
    overall_label: str = Field(..., description="Resumen global, ej. 'WCAG AA: PASS'")
    declarations: List[str] = Field(
        default_factory=list, description="Declaraciones: no depender solo del color, tamaño de fuente, etc."
    )


class DesignRecommendation(BaseModel):
    style_name: str = Field(..., description="Estilo del dashboard (ej. Modern analytical / Executive)")
    canvas: str = Field("16:9", description="Proporción del lienzo")
    layout: str = Field("12-column grid", description="Retícula de composición")
    spacing: str = Field("8px base grid", description="Base de espaciado")
    cards: str = Field("Moderate radius", description="Radio de las tarjetas")
    typography: str = Field(..., description="Jerarquía tipográfica")
    density: str = Field("Medium", description="Densidad visual")
    color_strategy: str = Field("Neutral base + semantic accent", description="Estrategia de color")
    notes: List[str] = Field(default_factory=list, description="Notas de composición profesional")


class DesignSystem(BaseModel):
    style: DesignRecommendation = Field(..., description="Recomendación estética principal")
    style_variants: List[DesignRecommendation] = Field(
        default_factory=list, description="Estilos alternativos para que el usuario elija"
    )
    palette: ColorPalette = Field(..., description="Paleta principal validada WCAG")
    palette_variants: List[ColorPalette] = Field(
        default_factory=list, description="Paletas alternativas validadas WCAG"
    )
    accessibility: AccessibilityRecommendation = Field(..., description="Validación de accesibilidad del sistema")


# ────────────────────────── DAX y guía Power BI ──────────────────────────────


class DaxMeasure(BaseModel):
    name: str = Field(..., description="Nombre de la medida DAX")
    formula: str = Field(..., description="Fórmula DAX completa")
    table_context: str = Field(..., description="Tabla del modelo donde se define")
    purpose: str = Field(..., description="Propósito de negocio de la medida")
    validated: bool = Field(..., description="True si referencia columnas reales; False si es propuesta")
    kind: str = Field("base", description="base (agregación directa) o business (derivada)")


class PowerBIImplementationInstruction(BaseModel):
    page: str = Field(..., description="Página del dashboard destino")
    visual: str = Field(..., description="Nombre del visual")
    visual_type: str = Field(..., description="Tipo de visual en Power BI")
    axis: Optional[str] = Field(None, description="Campo del Eje X")
    legend: Optional[str] = Field(None, description="Campo de leyenda")
    values: Optional[str] = Field(None, description="Campo de valores")
    filters: Optional[str] = Field(None, description="Filtro a aplicar")
    suggested_measure: Optional[str] = Field(None, description="Medida DAX sugerida")
    formatting: str = Field(..., description="Indicaciones de formato")
    accessibility: str = Field(..., description="Indicaciones de accesibilidad")


# ────────────────────────── DQ y validación ──────────────────────────────────


class DataQualityNote(BaseModel):
    column: str = Field(..., description="Columna cualificada Tabla[Columna]")
    completeness_pct: float = Field(..., description="Completitud real calculada")
    severity: str = Field("low", description="low, medium o high")
    message: str = Field(..., description="Explicación del impacto en el dashboard")


class DashboardCheck(BaseModel):
    check_id: str = Field(..., description="ID del chequeo")
    name: str = Field(..., description="Nombre legible del chequeo")
    category: CheckCategoryEnum = Field(..., description="integrity (bloqueante) o quality (advertencia)")
    passed: bool = Field(..., description="Resultado del chequeo")
    detail: str = Field(..., description="Detalle del resultado")


class DashboardValidation(BaseModel):
    checks: List[DashboardCheck] = Field(default_factory=list)
    passed_count: int = Field(..., description="Chequeos superados")
    total_count: int = Field(..., description="Total de chequeos")
    status: ValidationStatusEnum = Field(..., description="VALID, WARNING o INVALID")
    issues: List[str] = Field(default_factory=list, description="Problemas encontrados (legibles y accionables)")


class GenerationMeta(BaseModel):
    duration_ms: float = Field(..., description="Duración de la generación en milisegundos")
    dashboard_generation_total: int = Field(0, description="Contador acumulado de generaciones")
    dashboard_generation_failed: int = Field(0)
    dashboard_validation_failed: int = Field(0)
    visual_recommendation_count: int = Field(0)
    wcag_validation_failed: int = Field(0)
    deterministic: bool = Field(True, description="La generación es determinista y repetible")


# ────────────────────────── Blueprint final ──────────────────────────────────


class DashboardBlueprint(BaseModel):
    blueprint_id: str = Field(..., description="ID determinista (hash) del blueprint")
    model_id: str = Field(..., description="Modelo estrella origen")
    dataset_ids: List[str] = Field(default_factory=list, description="Datasets usados")
    name: str = Field(..., description="Nombre recomendado del dashboard")
    dashboard_type: DashboardTypeEnum = Field(..., description="Tipo de dashboard recomendado")
    objective: str = Field(..., description="Objetivo analítico del dashboard")
    audience: str = Field(..., description="Audiencia recomendada")
    business_questions: List[BusinessQuestion] = Field(default_factory=list, description="Preguntas de negocio")
    pages: List[DashboardPage] = Field(default_factory=list, description="Páginas propuestas")
    visuals: List[VisualRecommendation] = Field(default_factory=list, description="Visuals del dashboard")
    kpis: List[KPIRecommendation] = Field(default_factory=list, description="KPIs recomendados")
    filters: List[FilterRecommendation] = Field(default_factory=list, description="Filtros/slicers")
    hierarchies: List[HierarchyRecommendation] = Field(default_factory=list, description="Jerarquías")
    design: DesignSystem = Field(..., description="Sistema de diseño con paleta y WCAG")
    dax_measures: List[DaxMeasure] = Field(default_factory=list, description="Medidas DAX sugeridas")
    power_bi_implementation: List[PowerBIImplementationInstruction] = Field(
        default_factory=list, description="Guía de implementación en Power BI"
    )
    power_bi_summary: str = Field("", description="Resumen ejecutivo de la guía de implementación")
    semantic_model: SemanticModelAnalysis = Field(..., description="Análisis semántico del modelo")
    data_quality: List[DataQualityNote] = Field(default_factory=list, description="Notas de Data Quality integradas")
    warnings: List[str] = Field(default_factory=list, description="Advertencias del blueprint")
    limitations: List[str] = Field(default_factory=list, description="Limitaciones de los datos detectadas")
    confidence: ConfidenceLevelEnum = Field(..., description="Confianza del dashboard completo")
    confidence_rationale: str = Field(..., description="Metodología de la confianza")
    uncertainty_note: Optional[str] = Field(None, description="Nota de incertidumbre cuando las señales son débiles")
    validation: Optional[DashboardValidation] = Field(None, description="Validación integral determinista")
    generation_meta: GenerationMeta = Field(..., description="Metadatos de generación y observabilidad")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ────────────────────────── Requests/Responses API ───────────────────────────


class DashboardAnalyzeRequest(BaseModel):
    dataset_ids: List[str] = Field(..., min_length=1, description="IDs de los datasets que forman el modelo estrella")
    model_id: Optional[str] = Field(None, description="ID de modelo estrella ya generado (opcional)")


class DashboardValidateRequest(BaseModel):
    dataset_ids: List[str] = Field(..., min_length=1, description="Datasets contra los que validar")
    blueprint: DashboardBlueprint = Field(..., description="Blueprint a validar (posiblemente editado por el usuario)")


class DashboardStats(BaseModel):
    dashboard_generation_total: int = Field(0)
    dashboard_generation_failed: int = Field(0)
    dashboard_generation_duration_ms_total: float = Field(0.0)
    dashboard_validation_total: int = Field(0)
    dashboard_validation_failed: int = Field(0)
    visual_recommendation_count: int = Field(0)
    wcag_validation_failed: int = Field(0)
    cached_blueprints: int = Field(0)


class DashboardEditableOptions(BaseModel):
    """Opciones pre-validadas que el usuario puede elegir sin romper la integridad."""

    dashboard_types: List[DashboardTypeEnum] = Field(default_factory=list)
    palette_names: List[str] = Field(default_factory=list)
    style_names: List[str] = Field(default_factory=list)
    visual_alternatives: Dict[str, List[VisualTypeEnum]] = Field(default_factory=dict)


__all__ = [
    "DashboardBlueprint",
    "DashboardPage",
    "KPIRecommendation",
    "VisualRecommendation",
    "FilterRecommendation",
    "DesignRecommendation",
    "AccessibilityRecommendation",
    "DashboardValidation",
]
