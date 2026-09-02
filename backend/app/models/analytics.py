from typing import Dict, List, Optional

from pydantic import BaseModel


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


class ExcelFormulaItem(BaseModel):
    title: str
    column: str
    excel_column_letter: str
    formula_es: str
    formula_en: str
    description: str


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
