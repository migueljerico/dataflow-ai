from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BusinessKPI(BaseModel):
    id: str
    title: str
    value: str
    numeric_value: Optional[float] = None
    change_direction: Optional[str] = None  # 'positive', 'negative', 'neutral'
    subtitle: str
    category: str  # 'operaciones', 'financiero', 'calidad', 'general'


class CategoryDistribution(BaseModel):
    category_name: str
    count: int
    percentage: float
    secondary_metric_name: Optional[str] = None
    secondary_metric_value: Optional[float] = None


class ClusterPoint(BaseModel):
    row_index: int
    x: float
    y: float
    cluster_id: int
    label: Optional[str] = None


class ClusterSummaryItem(BaseModel):
    cluster_id: int
    label: str
    count: int
    percentage: float
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    feature_averages: Dict[str, float] = {}


class ClusterVisualization(BaseModel):
    cluster_column: str
    x_column: str
    y_column: str
    available_numeric_columns: List[str]
    total_points: int
    clusters: List[ClusterSummaryItem]
    points: List[ClusterPoint]


class BoxPlotData(BaseModel):
    column: str
    min: float
    q1: float
    median: float
    q3: float
    max: float
    lower_whisker: float
    upper_whisker: float
    iqr: float
    mean: float
    std: float
    outliers_count: int
    outlier_percentage: float
    sample_outliers: List[float] = []


class OutlierScatterPoint(BaseModel):
    row_index: int
    x_value: float
    y_value: float
    is_outlier: bool
    label: Optional[str] = None
    raw_y_value: Optional[float] = None
    was_modified: bool = False
    diff_status: Optional[str] = None


class OutlierDiffSummary(BaseModel):
    raw_outliers_count: int
    clean_outliers_count: int
    resolved_outliers_count: int
    reduction_percentage: float


class OutlierVisualization(BaseModel):
    columns: List[BoxPlotData]
    active_column: str
    scatter_points: Optional[List[OutlierScatterPoint]] = None
    raw_scatter_points: Optional[List[OutlierScatterPoint]] = None
    diff_summary: Optional[OutlierDiffSummary] = None
    total_outliers_detected: int
    detection_method: str = "IQR (1.5x) / Z-Score (>3.0)"


class IntegrationColumn(BaseModel):
    name: str
    python_dtype: str
    power_bi_m_type: str
    semantic_role: str  # 'id', 'numeric', 'date', 'category', 'boolean'
    excel_column_letter: Optional[str] = None


class DaxMeasureItem(BaseModel):
    name: str
    formula: str
    description: str
    category: str  # 'kpi', 'calidad', 'numerico', 'tiempo'
    format_string: Optional[str] = None
    display_folder: Optional[str] = None


class ExcelFormulaItem(BaseModel):
    title: str
    column: str
    excel_column_letter: str
    formula_es: str
    formula_en: str
    description: str
    category: str = "outlier"  # 'outlier', 'kpi', 'relative', 'conditional'
    target_cell: Optional[str] = None


class IntegrationGuide(BaseModel):
    table_name: str
    clean_filename: str
    parquet_filename: Optional[str] = None
    row_count: int
    columns: List[IntegrationColumn]
    power_query_m_csv: str
    power_query_m_parquet: Optional[str] = None
    dax_measures: List[DaxMeasureItem]
    excel_formulas: List[ExcelFormulaItem]
    tmdl_table_definition: Optional[str] = None
    tmdl_model_definition: Optional[str] = None
    dax_script: Optional[str] = None
    star_schema: Optional["StarSchemaDiagram"] = None


class StarSchemaDimension(BaseModel):
    name: str  # 'Dim_Cliente', 'Dim_Fecha'
    kind: str  # 'attribute' | 'calendar'
    source_column: str  # Columna original en la tabla de hechos
    key_column: str  # Columna clave de la dimension ('Date' en calendarios)
    distinct_count: int
    suggested_attributes: List[str] = []
    dax_definition: Optional[str] = None
    tmdl_definition: Optional[str] = None


class StarSchemaRelationship(BaseModel):
    from_table: str  # Lado muchos (tabla de hechos)
    from_column: str
    to_table: str  # Lado uno (dimension)
    to_column: str
    cardinality: str = "many-to-one"  # '*:1'
    cross_filter: str = "single"  # Direccion del filtro en Power BI
    is_active: bool = True


class StarSchemaDiagram(BaseModel):
    fact_table: str
    fact_rows: int
    measures: List[str]
    dimension_count: int
    dimensions: List[StarSchemaDimension]
    relationships: List[StarSchemaRelationship]
    dax_calculated_tables: str  # Script DAX consolidado de tablas calculadas
    tmdl_relationships: Optional[str] = None  # Fragmento TMDL de relaciones del modelo


class PercentileMetrics(BaseModel):
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    std: float
    iqr: float
    min_val: float
    max_val: float


class PercentileShift(BaseModel):
    p05_shift_pct: float
    p25_shift_pct: float
    p50_shift_pct: float
    p75_shift_pct: float
    p95_shift_pct: float
    max_shift_pct: float


class DriftStatusEnum(str, Enum):
    STABLE = "stable"
    MODERATE = "moderate"
    CRITICAL = "critical"


class DriftAlertSeverityEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DriftAlert(BaseModel):
    id: str
    column: str
    severity: DriftAlertSeverityEnum
    title: str
    message: str
    metric: str
    value: float
    threshold: float


class ProactiveRecommendation(BaseModel):
    id: str
    column: Optional[str] = None
    category: str  # 'drift', 'anomaly', 'distribution', 'governance'
    priority: str  # 'high', 'medium', 'low'
    action_type: str  # 'capping', 'segmentation', 'imputation_review', 'verified_stable'
    title: str
    rationale: str
    suggested_step: Optional[str] = None


class ColumnDriftReport(BaseModel):
    column_name: str
    raw_percentiles: Optional[PercentileMetrics] = None
    clean_percentiles: PercentileMetrics
    shift: Optional[PercentileShift] = None
    drift_score: float  # 0.0 a 100.0 (porcentaje de desvío de distribución)
    drift_status: DriftStatusEnum
    ks_statistic: Optional[float] = None
    p_value: Optional[float] = None
    anomaly_count: int
    anomaly_percentage: float
    alerts: List[DriftAlert] = []
    recommendations: List[ProactiveRecommendation] = []


class DriftAnalysisReport(BaseModel):
    columns: List[ColumnDriftReport]
    overall_drift_status: DriftStatusEnum
    stable_columns_count: int
    moderate_columns_count: int
    critical_columns_count: int
    total_alerts: int
    alerts: List[DriftAlert] = []
    global_recommendations: List[ProactiveRecommendation] = []
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutiveAnalyticsReport(BaseModel):
    run_id: str
    dataset_name: str
    domain: str  # 'contact_center', 'sales', 'people_analytics', 'general'
    kpis: List[BusinessKPI]
    executive_summary: str
    strategic_recommendations: List[str]
    category_breakdown: Optional[List[CategoryDistribution]] = None
    cluster_visualization: Optional[ClusterVisualization] = None
    outlier_visualization: Optional[OutlierVisualization] = None
    integration_guide: Optional[IntegrationGuide] = None
    drift_analysis: Optional[DriftAnalysisReport] = None
