import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExecutionReport } from './ExecutionReport';
import { LanguageProvider } from '../context/LanguageContext';
import { ExecutionResult } from '../types';

// Mock de BusinessInsights para centrar el test unitario en ExecutionReport
vi.mock('./BusinessInsights', () => ({
  BusinessInsights: () => <div data-testid="business-insights-mock">Business Insights Mock</div>,
}));

const mockResult: ExecutionResult = {
  run_id: 'RUN-test-1234',
  dataset_id: 'DS-test-1234',
  plan_id: 'PLAN-test-1234',
  status: 'completed',
  started_at: '2026-08-31T10:00:00Z',
  finished_at: '2026-08-31T10:00:01Z',
  rows_before: 100,
  rows_after: 95,
  columns_before: 10,
  columns_after: 10,
  applied_steps_count: 3,
  input_hash_md5: 'md5_input_hash',
  output_hash_md5: 'md5_output_hash',
  clean_filename: 'clean_data.csv',
  download_url: '/api/v1/runs/RUN-test-1234/download',
  script_url: '/api/v1/runs/RUN-test-1234/download-script',
  parquet_filename: 'clean_data.parquet',
  parquet_url: '/api/v1/runs/RUN-test-1234/download-parquet',
  audit_logs: ['[VALIDACIÓN OK] Paso 1 aplicado', '[VALIDACIÓN OK] Paso 2 aplicado'],
  errors: [],
  warnings: [],
};

describe('ExecutionReport Component', () => {
  it('renders execution statistics and action buttons including Parquet download', () => {
    const handleReset = vi.fn();
    render(
      <LanguageProvider>
        <ExecutionReport result={mockResult} reportBeforeAfter={null} onResetSession={handleReset} />
      </LanguageProvider>
    );

    // Run ID
    expect(screen.getByText('RUN-test-1234')).toBeInTheDocument();

    // Statistics
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('95')).toBeInTheDocument();
    expect(screen.getByText(/3 Pasos/i)).toBeInTheDocument();

    // Audit logs
    expect(screen.getByText('[VALIDACIÓN OK] Paso 1 aplicado')).toBeInTheDocument();

    // Download links
    const csvLink = screen.getByRole('link', { name: /clean_data\.csv/i });
    expect(csvLink).toHaveAttribute('href', '/api/v1/runs/RUN-test-1234/download');

    const parquetLink = screen.getByRole('link', { name: /clean_data\.parquet/i });
    expect(parquetLink).toHaveAttribute('href', '/api/v1/runs/RUN-test-1234/download-parquet');

    const scriptLink = screen.getByRole('link', { name: /Python/i });
    expect(scriptLink).toHaveAttribute('href', '/api/v1/runs/RUN-test-1234/download-script');
  });
});
