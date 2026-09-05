import { 
  DatasetMetadata, 
  ProfilingReport, 
  QualityReport, 
  TransformationPlan, 
  TransformationStep, 
  ExecutionResult,
  SampleDataset,
  ExecutiveAnalyticsReport,
  OpenDatasetItem,
  OpenDataSearchResponse,
  CacheStats,
  ExecutionSummaryItem,
  QualityComparisonReport,
  DriftSimulationResult,
  ReportSchedule,
  ReportScheduleCreate,
  ReportScheduleListResponse,
  ScheduleExecutionLog,
  MultiTableStarSchema,
} from '../types';
import { getApiKey } from '../utils/security';

const API_BASE = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Error HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      if (errorJson.message) {
        errorMsg = errorJson.message;
      } else if (errorJson.detail) {
        errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  // Datasets
  uploadDataset: async (file: File): Promise<DatasetMetadata> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DatasetMetadata>(res);
  },

  uploadDatasetsBatch: async (files: File[]): Promise<DatasetMetadata[]> => {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    const res = await fetch(`${API_BASE}/datasets/upload-batch`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DatasetMetadata[]>(res);
  },

  loadDatasetFromUrl: async (url: string): Promise<DatasetMetadata> => {
    const res = await fetch(`${API_BASE}/datasets/from-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    return handleResponse<DatasetMetadata>(res);
  },

  listSampleDatasets: async (): Promise<SampleDataset[]> => {
    const res = await fetch(`${API_BASE}/datasets/samples`);
    return handleResponse<SampleDataset[]>(res);
  },

  getFeaturedOpenDatasets: async (): Promise<OpenDatasetItem[]> => {
    const res = await fetch(`${API_BASE}/datasets/open-data/featured`);
    return handleResponse<OpenDatasetItem[]>(res);
  },

  searchOpenDatasets: async (query?: string, limit: number = 10): Promise<OpenDataSearchResponse> => {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    params.append('limit', limit.toString());
    const res = await fetch(`${API_BASE}/datasets/open-data/search?${params.toString()}`);
    return handleResponse<OpenDataSearchResponse>(res);
  },

  loadSampleDataset: async (sampleId: string): Promise<DatasetMetadata> => {
    const res = await fetch(`${API_BASE}/datasets/samples/${sampleId}/load`, {
      method: 'POST',
    });
    return handleResponse<DatasetMetadata>(res);
  },

  getDatasetMetadata: async (datasetId: string): Promise<DatasetMetadata> => {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}`);
    return handleResponse<DatasetMetadata>(res);
  },

  // Profiling
  getProfilingReport: async (datasetId: string): Promise<ProfilingReport> => {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/profiling`);
    return handleResponse<ProfilingReport>(res);
  },
  getProfiling: async (datasetId: string): Promise<ProfilingReport> => {
    return api.getProfilingReport(datasetId);
  },

  // Quality
  getQualityReport: async (datasetId: string): Promise<QualityReport> => {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/quality`);
    return handleResponse<QualityReport>(res);
  },
  getQuality: async (datasetId: string): Promise<QualityReport> => {
    return api.getQualityReport(datasetId);
  },

  // Plans
  proposePlanFromRules: async (datasetId: string): Promise<TransformationPlan> => {
    const res = await fetch(`${API_BASE}/plans/propose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId }),
    });
    return handleResponse<TransformationPlan>(res);
  },
  proposePlan: async (datasetId: string): Promise<TransformationPlan> => {
    return api.proposePlanFromRules(datasetId);
  },

  proposeAIPlan: async (datasetId: string, provider?: string, apiKey?: string): Promise<TransformationPlan> => {
    const storedKey = apiKey || getApiKey() || undefined;
    const effectiveProvider = provider || (storedKey ? 'gemini' : 'mock');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (storedKey) headers['X-Gemini-Api-Key'] = storedKey;
    const res = await fetch(`${API_BASE}/plans/propose/ai`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ dataset_id: datasetId, provider: effectiveProvider }),
    });
    return handleResponse<TransformationPlan>(res);
  },

  approveAndExecutePlan: async (planId: string, steps: TransformationStep[]): Promise<ExecutionResult> => {
    const res = await fetch(`${API_BASE}/plans/${planId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps }),
    });
    return handleResponse<ExecutionResult>(res);
  },

  getRunResult: async (runId: string): Promise<ExecutionResult> => {
    const res = await fetch(`${API_BASE}/runs/${runId}`);
    return handleResponse<ExecutionResult>(res);
  },

  getRunQualityReport: async (runId: string): Promise<ExecutionResult | null> => {
    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/report`);
      return handleResponse<ExecutionResult>(res);
    } catch {
      return null;
    }
  },

  getQualityComparison: async (runId: string): Promise<QualityComparisonReport> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/quality-comparison`);
    return handleResponse<QualityComparisonReport>(res);
  },

  getRunsHistory: async (datasetId?: string): Promise<ExecutionSummaryItem[]> => {
    const url = datasetId ? `${API_BASE}/runs?dataset_id=${encodeURIComponent(datasetId)}` : `${API_BASE}/runs`;
    const res = await fetch(url);
    return handleResponse<ExecutionSummaryItem[]>(res);
  },

  compareRuns: async (runA: string, runB: string): Promise<QualityComparisonReport> => {
    const res = await fetch(`${API_BASE}/runs/compare?run_a=${encodeURIComponent(runA)}&run_b=${encodeURIComponent(runB)}`);
    return handleResponse<QualityComparisonReport>(res);
  },

  getBatchZipDownloadUrl: (runIds: string[]): string => {
    return `${API_BASE}/runs/batch/download-zip?run_ids=${encodeURIComponent(runIds.join(','))}`;
  },

  // Business Analytics
  getBusinessAnalytics: async (runId: string): Promise<ExecutiveAnalyticsReport> => {
    const res = await fetch(`${API_BASE}/analytics/${runId}`);
    return handleResponse<ExecutiveAnalyticsReport>(res);
  },

  getExecutiveReportExportUrl: (runId: string, lang: string = 'es'): string => {
    return `${API_BASE}/analytics/${runId}/export?lang=${encodeURIComponent(lang)}`;
  },

  getTmdlExportUrl: (runId: string): string => {
    return `${API_BASE}/analytics/${runId}/export/tmdl`;
  },

  getDaxExportUrl: (runId: string): string => {
    return `${API_BASE}/analytics/${runId}/export/dax`;
  },

  getPbipExportUrl: (runId: string): string => {
    return `${API_BASE}/analytics/${runId}/export/pbip`;
  },

  // Observabilidad de Caché
  getCacheStats: async (): Promise<CacheStats> => {
    const res = await fetch(`${API_BASE}/cache/stats`);
    return handleResponse<CacheStats>(res);
  },

  // Simulación interactiva de drift (hipotética, antes de la aprobación formal)
  simulateDrift: async (datasetId: string, steps: TransformationStep[]): Promise<DriftSimulationResult> => {
    const res = await fetch(`${API_BASE}/simulations/drift`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, steps }),
    });
    return handleResponse<DriftSimulationResult>(res);
  },

  // Reportes ejecutivos PDF/HTML y exportación programada con webhooks
  getExecutiveReportPdfUrl: (runId: string, lang: string = 'es'): string =>
    `${API_BASE}/reports/${runId}/pdf?lang=${encodeURIComponent(lang)}`,

  getExecutiveReportHtmlUrl: (runId: string, lang: string = 'es'): string =>
    `${API_BASE}/reports/${runId}/html?lang=${encodeURIComponent(lang)}`,

  createReportSchedule: async (payload: ReportScheduleCreate): Promise<ReportSchedule> => {
    const res = await fetch(`${API_BASE}/reports/schedules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<ReportSchedule>(res);
  },

  listReportSchedules: async (): Promise<ReportScheduleListResponse> => {
    const res = await fetch(`${API_BASE}/reports/schedules`);
    return handleResponse<ReportScheduleListResponse>(res);
  },

  runReportScheduleNow: async (scheduleId: string): Promise<ScheduleExecutionLog> => {
    const res = await fetch(`${API_BASE}/reports/schedules/${scheduleId}/run-now`, { method: 'POST' });
    return handleResponse<ScheduleExecutionLog>(res);
  },

  deleteReportSchedule: async (scheduleId: string): Promise<{ deleted: boolean }> => {
    const res = await fetch(`${API_BASE}/reports/schedules/${scheduleId}`, { method: 'DELETE' });
    return handleResponse<{ deleted: boolean }>(res);
  },

  getScheduledLastReportUrl: (scheduleId: string): string =>
    `${API_BASE}/reports/schedules/${scheduleId}/last-report`,

  // Relational & Multi-Table Star Schema
  generateStarSchema: async (datasetIds: string[]): Promise<MultiTableStarSchema> => {
    const res = await fetch(`${API_BASE}/relational/star-schema`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_ids: datasetIds }),
    });
    return handleResponse<MultiTableStarSchema>(res);
  },

  getStarSchemaTmdlUrl: (modelId: string): string =>
    `${API_BASE}/relational/models/${modelId}/tmdl`,
};
