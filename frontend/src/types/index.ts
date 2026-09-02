export type FileType = 'csv' | 'xlsx';

export type ProcessingState = 
  | 'uploaded' 
  | 'validated' 
  | 'profiled' 
  | 'quality_analyzed' 
  | 'plan_proposed' 
  | 'pending_review' 
  | 'approved' 
  | 'executing' 
  | 'completed'
  | 'validation_failed'
  | 'profiling_failed'
  | 'plan_invalid'
  | 'execution_failed';

export interface DatasetMetadata {
  dataset_id: string;
  filename: string;
  file_type: FileType;
  size_bytes: number;
  row_count: number;
  column_count: number;
  columns: string[];
  created_at: string;
  status: ProcessingState;
  warnings: string[];
}

export type ColumnType = 'numeric' | 'datetime' | 'text' | 'boolean' | 'categorical';
export type SemanticHint = 'id' | 'email' | 'currency' | 'percentage' | 'date' | 'phone' | 'location' | 'name' | 'unknown';

export interface ColumnProfile {
  column_name: string;
  inferred_type: ColumnType;
  semantic_hint: SemanticHint;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: unknown[];
  min_value?: number;
  max_value?: number;
  mean?: number;
  median?: number;
  std?: number;
  warnings: string[];
}

export interface ProfilingReport {
  dataset_id: string;
  row_count: number;
  column_count: number;
  duplicates_count: number;
  duplicates_percentage: number;
  memory_estimate_bytes: number;
  columns: ColumnProfile[];
  global_warnings: string[];
  generated_at: string;
}

export type QualityDimension = 'completeness' | 'uniqueness' | 'consistency' | 'validity' | 'integrity';
export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface QualityIssue {
  issue_id: string;
  dimension: QualityDimension;
  severity: Severity;
  column?: string;
  description: string;
  affected_rows: number;
  affected_percentage: number;
  evidence_sample: unknown[];
  suggested_action: string;
}

export interface DimensionBreakdown {
  score: number;
  weight: number;
  issues_count: number;
  summary: string;
}

export interface QualityScore {
  overall_score: number;
  completeness: DimensionBreakdown;
  validity: DimensionBreakdown;
  consistency: DimensionBreakdown;
  uniqueness: DimensionBreakdown;
  integrity: DimensionBreakdown;
  explanation: string;
}

export interface QualityReport {
  dataset_id: string;
  quality_score: QualityScore;
  issues: QualityIssue[];
  issues_count: number;
  generated_at: string;
}

export type StepStatus = 'proposed' | 'approved' | 'edited' | 'rejected';

export interface TransformationStep {
  step_id: string;
  operation: string;
  column?: string;
  parameters: Record<string, unknown>;
  reason: string;
  confidence: number;
  risk: 'low' | 'medium' | 'high';
  affected_rows_estimate: number;
  status: StepStatus;
  data_loss_warning?: string;
}

export interface AIMetrics {
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  model: string;
  provider: string;
  cached?: boolean;
}

export interface TransformationPlan {
  plan_id: string;
  dataset_id: string;
  summary: string;
  steps: TransformationStep[];
  source: string;
  created_at: string;
  warnings?: string[];
  ai_metrics?: AIMetrics;
}

export interface ExecutionResult {
  run_id: string;
  dataset_id: string;
  plan_id: string;
  status: string;
  started_at: string;
  finished_at: string;
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  applied_steps_count: number;
  input_hash_md5: string;
  output_hash_md5: string;
  clean_filename: string;
  download_url: string;
  script_url: string;
  parquet_filename?: string;
  parquet_url?: string;
  audit_logs?: string[];
  errors: string[];
  warnings: string[];
}

export interface SampleDataset {
  id: string;
  title: string;
  filename: string;
  description: string;
  icon: string;
}

export interface BusinessKPI {
  id: string;
  title: string;
  value: string;
  numeric_value?: number;
  change_direction?: 'positive' | 'negative' | 'neutral';
  subtitle: string;
  category: string;
}

export interface CategoryDistribution {
  category_name: string;
  count: number;
  percentage: number;
  secondary_metric_name?: string;
  secondary_metric_value?: number;
}

export interface ClusterPoint {
  row_index: number;
  x: number;
  y: number;
  cluster_id: number;
  label?: string;
}

export interface ClusterSummaryItem {
  cluster_id: number;
  label: string;
  count: number;
  percentage: number;
  center_x?: number;
  center_y?: number;
  feature_averages: Record<string, number>;
}

export interface ClusterVisualization {
  cluster_column: string;
  x_column: string;
  y_column: string;
  available_numeric_columns: string[];
  total_points: number;
  clusters: ClusterSummaryItem[];
  points: ClusterPoint[];
}

export interface BoxPlotData {
  column: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  lower_whisker: number;
  upper_whisker: number;
  iqr: number;
  mean: number;
  std: number;
  outliers_count: number;
  outlier_percentage: number;
  sample_outliers: number[];
}

export interface OutlierScatterPoint {
  row_index: number;
  x_value: number;
  y_value: number;
  is_outlier: boolean;
  label?: string;
  raw_y_value?: number;
  was_modified?: boolean;
  diff_status?: 'clamped' | 'resolved_outlier' | 'imputed' | 'unchanged' | string;
}

export interface OutlierDiffSummary {
  raw_outliers_count: number;
  clean_outliers_count: number;
  resolved_outliers_count: number;
  reduction_percentage: number;
}

export interface OutlierVisualization {
  columns: BoxPlotData[];
  active_column: string;
  scatter_points?: OutlierScatterPoint[];
  raw_scatter_points?: OutlierScatterPoint[];
  diff_summary?: OutlierDiffSummary;
  total_outliers_detected: number;
  detection_method: string;
}

export interface IntegrationColumn {
  name: string;
  python_dtype: string;
  power_bi_m_type: string;
  semantic_role: string;
  excel_column_letter?: string;
}

export interface DaxMeasureItem {
  name: string;
  formula: string;
  description: string;
  category: string;
  format_string?: string;
  display_folder?: string;
}

export interface ExcelFormulaItem {
  title: string;
  column: string;
  excel_column_letter: string;
  formula_es: string;
  formula_en: string;
  description: string;
  category?: string;
  target_cell?: string;
}

export interface IntegrationGuide {
  table_name: string;
  clean_filename: string;
  parquet_filename?: string;
  row_count: number;
  columns: IntegrationColumn[];
  power_query_m_csv: string;
  power_query_m_parquet?: string;
  dax_measures: DaxMeasureItem[];
  excel_formulas: ExcelFormulaItem[];
  tmdl_table_definition?: string;
  tmdl_model_definition?: string;
  dax_script?: string;
}

export interface ExecutiveAnalyticsReport {
  run_id: string;
  dataset_name: string;
  domain: string;
  kpis: BusinessKPI[];
  executive_summary: string;
  strategic_recommendations: string[];
  category_breakdown?: CategoryDistribution[];
  cluster_visualization?: ClusterVisualization;
  outlier_visualization?: OutlierVisualization;
  integration_guide?: IntegrationGuide;
}

export interface OpenDatasetItem {
  id: string;
  title: string;
  description: string;
  organization: string;
  resource_url: string;
  format: string;
  size_bytes?: number;
  tags: string[];
}

export interface OpenDataSearchResponse {
  total: number;
  results: OpenDatasetItem[];
  source: string;
}

