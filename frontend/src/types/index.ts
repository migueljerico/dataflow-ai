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
export type SemanticHint = 'id' | 'email' | 'currency' | 'percentage' | 'fraction' | 'date' | 'phone' | 'location' | 'name' | 'unknown';

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

export interface StarSchemaDimension {
  name: string;
  kind: string; // 'attribute' | 'calendar'
  source_column: string;
  key_column: string;
  distinct_count: number;
  suggested_attributes: string[];
  dax_definition?: string;
  tmdl_definition?: string;
}

export interface CacheStats {
  backend: string;
  distributed: boolean;
  redis_available: boolean;
  redis_hits: number;
  redis_errors: number;
  hits: number;
  l1_hits: number;
  l2_hits: number;
  misses: number;
  total_requests: number;
  hit_rate_pct: number;
  l1_hit_rate_pct: number;
  l2_hit_rate_pct: number;
  cached_entries: number;
  saved_tokens: number;
  saved_cost_usd: number;
}

export interface StarSchemaRelationship {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  cardinality: string; // 'many-to-one'
  cross_filter: string;
  is_active: boolean;
}

export interface StarSchemaDiagram {
  fact_table: string;
  fact_rows: number;
  measures: string[];
  dimension_count: number;
  dimensions: StarSchemaDimension[];
  relationships: StarSchemaRelationship[];
  dax_calculated_tables: string;
  tmdl_relationships?: string;
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
  star_schema?: StarSchemaDiagram;
}

export interface DimensionComparison {
  dimension: QualityDimension;
  score_before: number;
  score_after: number;
  delta: number;
  issues_before: number;
  issues_after: number;
  summary: string;
}

export interface QualityComparisonReport {
  run_id: string;
  dataset_id: string;
  overall_score_before: number;
  overall_score_after: number;
  delta_score: number;
  dimensions: DimensionComparison[];
  issues_count_before: number;
  issues_count_after: number;
  issues_resolved_count: number;
  explanation: string;
  generated_at: string;
}

export interface ExecutionSummaryItem {
  run_id: string;
  dataset_id: string;
  filename: string;
  clean_filename: string;
  status: string;
  started_at: string;
  finished_at: string;
  execution_time_seconds: number;
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  applied_steps_count: number;
  score_before: number;
  score_after: number;
  score_delta: number;
  input_hash_md5: string;
  output_hash_md5: string;
  download_url: string;
  parquet_url?: string;
  script_url?: string;
}

export interface PercentileMetrics {
  p05: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  mean: number;
  std: number;
  iqr: number;
  min_val: number;
  max_val: number;
}

export interface PercentileShift {
  p05_shift_pct: number;
  p25_shift_pct: number;
  p50_shift_pct: number;
  p75_shift_pct: number;
  p95_shift_pct: number;
  max_shift_pct: number;
}

export type DriftStatus = 'stable' | 'moderate' | 'critical';
export type DriftAlertSeverity = 'info' | 'warning' | 'critical';

export interface DriftAlert {
  id: string;
  column: string;
  severity: DriftAlertSeverity;
  title: string;
  message: string;
  metric: string;
  value: number;
  threshold: number;
}

export interface ProactiveRecommendation {
  id: string;
  column?: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  action_type: string;
  title: string;
  rationale: string;
  suggested_step?: string;
}

export interface ColumnDriftReport {
  column_name: string;
  raw_percentiles?: PercentileMetrics;
  clean_percentiles: PercentileMetrics;
  shift?: PercentileShift;
  drift_score: number;
  drift_status: DriftStatus;
  ks_statistic?: number;
  p_value?: number;
  anomaly_count: number;
  anomaly_percentage: number;
  alerts: DriftAlert[];
  recommendations: ProactiveRecommendation[];
}

export interface DriftAnalysisReport {
  columns: ColumnDriftReport[];
  overall_drift_status: DriftStatus;
  stable_columns_count: number;
  moderate_columns_count: number;
  critical_columns_count: number;
  total_alerts: number;
  alerts: DriftAlert[];
  global_recommendations: ProactiveRecommendation[];
  generated_at: string;
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
  drift_analysis?: DriftAnalysisReport;
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



// ── v1.16.0: Simulación de drift y reportes programados ─────────────────────

export interface SimulatedStepOutcome {
  step_id: string;
  operation: string;
  column?: string | null;
  applied: boolean;
  rows_affected: number;
  error?: string | null;
}

export interface DriftSimulationResult {
  dataset_id: string;
  simulated: boolean;
  governance_note: string;
  hypothetical_steps: number;
  applied_steps: number;
  step_outcomes: SimulatedStepOutcome[];
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  drift_report: DriftAnalysisReport;
  elapsed_ms: number;
  generated_at: string;
}

export type ReportFormat = 'html' | 'pdf';
export type WebhookTrigger = 'always' | 'critical_drift';

export interface ReportScheduleCreate {
  run_id: string;
  report_format?: ReportFormat;
  interval_minutes?: number;
  webhook_url?: string | null;
  trigger?: WebhookTrigger;
  lang?: string;
}

export interface ReportSchedule {
  schedule_id: string;
  run_id: string;
  dataset_id: string;
  report_format: ReportFormat;
  interval_minutes: number;
  webhook_url?: string | null;
  trigger: WebhookTrigger;
  lang: string;
  enabled: boolean;
  created_at: string;
  next_run_at?: string | null;
  last_executed_at?: string | null;
  last_status?: string | null;
  last_drift_status?: DriftStatus | null;
  last_error?: string | null;
  executions_count: number;
  deliveries_count: number;
  last_report_key?: string | null;
}

export interface ReportScheduleListResponse {
  schedules: ReportSchedule[];
  total: number;
}

export interface WebhookDeliveryResult {
  delivered: boolean;
  reason: string;
  http_status?: number | null;
  error?: string | null;
}

export interface ScheduleExecutionLog {
  schedule_id: string;
  executed_at: string;
  report_format: ReportFormat;
  drift_status?: DriftStatus | null;
  report_key?: string | null;
  webhook?: WebhookDeliveryResult | null;
  error?: string | null;
}

export interface RelationshipIntegrityAudit {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  cardinality: string;
  total_fk_rows: number;
  matching_fk_rows: number;
  orphan_fk_rows: number;
  match_percentage: number;
  orphan_samples: unknown[];
  is_referential_clean: boolean;
}

export interface StarSchemaTableNode {
  table_id: string;
  table_name: string;
  role: 'fact' | 'dimension' | 'bridge' | 'unknown';
  row_count: number;
  column_count: number;
  primary_keys: string[];
  foreign_keys: string[];
  attributes: string[];
  measures: string[];
}

export interface MultiTableStarSchema {
  model_id: string;
  model_name: string;
  created_at: string;
  fact_table: StarSchemaTableNode;
  dimension_tables: StarSchemaTableNode[];
  relationships: RelationshipIntegrityAudit[];
  suggested_dax_measures: Record<string, string>;
  tmdl_definition: string;
  referential_integrity_score: number;
}

