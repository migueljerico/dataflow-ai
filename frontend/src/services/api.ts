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
  OpenDataSearchResponse
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
      const res = await fetch(`${API_BASE}/runs/${runId}`);
      return handleResponse<ExecutionResult>(res);
    } catch {
      return null;
    }
  },

  // Business Analytics
  getBusinessAnalytics: async (runId: string): Promise<ExecutiveAnalyticsReport> => {
    const res = await fetch(`${API_BASE}/analytics/${runId}`);
    return handleResponse<ExecutiveAnalyticsReport>(res);
  }
};
