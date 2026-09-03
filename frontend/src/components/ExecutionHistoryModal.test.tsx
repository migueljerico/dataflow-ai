import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutionHistoryModal } from './ExecutionHistoryModal';
import { LanguageProvider } from '../context/LanguageContext';
import { api } from '../services/api';
import { ExecutionSummaryItem, QualityComparisonReport } from '../types';

const mockRuns: ExecutionSummaryItem[] = [
  {
    run_id: 'RUN-002',
    dataset_id: 'DS-001',
    filename: 'ventas.csv',
    clean_filename: 'clean_ventas_v2.csv',
    status: 'completed',
    started_at: '2026-09-03T12:00:00Z',
    finished_at: '2026-09-03T12:00:02Z',
    execution_time_seconds: 2.1,
    rows_before: 120,
    rows_after: 110,
    columns_before: 8,
    columns_after: 8,
    applied_steps_count: 5,
    score_before: 75.0,
    score_after: 98.0,
    score_delta: 23.0,
    input_hash_md5: 'md5_1',
    output_hash_md5: 'md5_2',
    download_url: '/api/v1/runs/RUN-002/download',
  },
  {
    run_id: 'RUN-001',
    dataset_id: 'DS-001',
    filename: 'ventas.csv',
    clean_filename: 'clean_ventas_v1.csv',
    status: 'completed',
    started_at: '2026-09-03T11:00:00Z',
    finished_at: '2026-09-03T11:00:01Z',
    execution_time_seconds: 1.5,
    rows_before: 120,
    rows_after: 115,
    columns_before: 8,
    columns_after: 8,
    applied_steps_count: 2,
    score_before: 75.0,
    score_after: 88.0,
    score_delta: 13.0,
    input_hash_md5: 'md5_1',
    output_hash_md5: 'md5_3',
    download_url: '/api/v1/runs/RUN-001/download',
  },
];

const mockComparison: QualityComparisonReport = {
  run_id: 'RUN-001_vs_RUN-002',
  dataset_id: 'DS-001',
  overall_score_before: 88.0,
  overall_score_after: 98.0,
  delta_score: 10.0,
  dimensions: [
    {
      dimension: 'completeness' as any,
      score_before: 85.0,
      score_after: 100.0,
      delta: 15.0,
      issues_before: 2,
      issues_after: 0,
      summary: '100% Completo (+15 pts)',
    },
    {
      dimension: 'validity' as any,
      score_before: 80.0,
      score_after: 95.0,
      delta: 15.0,
      issues_before: 3,
      issues_after: 0,
      summary: '95% Válido (+15 pts)',
    },
  ],
  issues_count_before: 5,
  issues_count_after: 0,
  issues_resolved_count: 5,
  explanation: 'Mejora de 88.0 a 98.0 (+10 pts) entre versiones.',
  generated_at: '2026-09-03T12:00:05Z',
};

describe('ExecutionHistoryModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders history modal, loads runs, and performs version comparison', async () => {
    vi.spyOn(api, 'getRunsHistory').mockResolvedValue(mockRuns);
    vi.spyOn(api, 'compareRuns').mockResolvedValue(mockComparison);

    const handleClose = vi.fn();

    render(
      <LanguageProvider>
        <ExecutionHistoryModal
          isOpen={true}
          onClose={handleClose}
          currentRunId="RUN-002"
          datasetId="DS-001"
        />
      </LanguageProvider>
    );

    // Header y título
    expect(screen.getByText(/Historial de Ejecuciones/i)).toBeInTheDocument();

    // Comprobar filas de historial
    await waitFor(() => {
      expect(screen.getByText(/RUN-002/i)).toBeInTheDocument();
      expect(screen.getByText(/RUN-001/i)).toBeInTheDocument();
    });

    // Botón de comparar versiones
    const compareBtn = screen.getByRole('button', { name: /Comparar 2 Versiones/i });
    expect(compareBtn).toBeEnabled();

    // Disparar comparación
    fireEvent.click(compareBtn);

    // Verificar panel de comparación
    await waitFor(() => {
      expect(screen.getByText(/Comparativa de Calidad Dimensional/i)).toBeInTheDocument();
      expect(screen.getByText(/Mejora de 88.0 a 98.0/i)).toBeInTheDocument();
      expect(screen.getByText('+10 pts')).toBeInTheDocument();
    });
  });
});
