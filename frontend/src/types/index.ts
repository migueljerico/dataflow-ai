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
  sample_values: any[];
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
  evidence_sample: any[];
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
  parameters: Record<string, any>;
  reason: string;
  confidence: number;
  risk: 'low' | 'medium' | 'high';
  affected_rows_estimate: number;
  status: StepStatus;
}

export interface TransformationPlan {
  plan_id: string;
  dataset_id: string;
  summary: string;
  steps: TransformationStep[];
  source: string;
  created_at: string;
  warnings?: string[];
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

export interface ExecutiveAnalyticsReport {
  run_id: string;
  dataset_name: string;
  domain: string;
  kpis: BusinessKPI[];
  executive_summary: string;
  strategic_recommendations: string[];
  category_breakdown?: CategoryDistribution[];
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

