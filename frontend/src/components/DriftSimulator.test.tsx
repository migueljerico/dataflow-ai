import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DriftSimulator } from './DriftSimulator';
import { LanguageProvider } from '../context/LanguageContext';
import { api } from '../services/api';
import { DriftSimulationResult, TransformationStep } from '../types';

const mockSteps: TransformationStep[] = [
  {
    step_id: 'STEP-001',
    operation: 'trim_text',
    column: 'Nombre',
    parameters: { column: 'Nombre' },
    reason: 'limpiar espacios',
    confidence: 0.9,
    risk: 'low',
    affected_rows_estimate: 10,
    status: 'approved',
  },
  {
    step_id: 'STEP-002',
    operation: 'drop_column',
    column: 'Basura',
    parameters: { column: 'Basura' },
    reason: 'columna inútil',
    confidence: 0.8,
    risk: 'medium',
    affected_rows_estimate: 10,
    status: 'rejected',
  },
];

const mockSimulation: DriftSimulationResult = {
  dataset_id: 'DS-001',
  simulated: true,
  governance_note: 'SIMULACIÓN HIPOTÉTICA: el dataset no se modifica.',
  hypothetical_steps: 1,
  applied_steps: 1,
  step_outcomes: [
    { step_id: 'STEP-001', operation: 'trim_text', column: 'Nombre', applied: true, rows_affected: 10, error: null },
  ],
  rows_before: 100,
  rows_after: 100,
  columns_before: 8,
  columns_after: 8,
  elapsed_ms: 42.5,
  generated_at: '2026-09-03T12:00:00Z',
  drift_report: {
    columns: [
      {
        column_name: 'Salary',
        clean_percentiles: {
          p05: 50000, p25: 60000, p50: 75000, p75: 90000, p95: 110000,
          mean: 76000, std: 15000, iqr: 30000, min_val: 45000, max_val: 120000,
        },
        raw_percentiles: {
          p05: 48000, p25: 59000, p50: 74000, p75: 89000, p95: 112000,
          mean: 75000, std: 16000, iqr: 30000, min_val: 40000, max_val: 125000,
        },
        shift: {
          p05_shift_pct: 4.17, p25_shift_pct: 1.69, p50_shift_pct: 1.35,
          p75_shift_pct: 1.12, p95_shift_pct: -1.79, max_shift_pct: 4.17,
        },
        drift_score: 12.5,
        drift_status: 'moderate',
        ks_statistic: 0.08,
        p_value: 0.2,
        anomaly_count: 3,
        anomaly_percentage: 3.0,
        alerts: [],
        recommendations: [],
      },
    ],
    overall_drift_status: 'moderate',
    stable_columns_count: 0,
    moderate_columns_count: 1,
    critical_columns_count: 0,
    total_alerts: 0,
    alerts: [],
    global_recommendations: [],
    generated_at: '2026-09-03T12:00:00Z',
  },
};

describe('DriftSimulator Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('simula solo con los pasos no rechazados y muestra percentiles antes/después', async () => {
    const spy = vi.spyOn(api, 'simulateDrift').mockResolvedValue(mockSimulation);

    render(
      <LanguageProvider>
        <DriftSimulator datasetId="DS-001" steps={mockSteps} />
      </LanguageProvider>
    );

    const btn = screen.getByTestId('simulate-drift-btn');
    // Solo 1 paso simulable (el rechazado queda fuera)
    expect(btn.textContent).toContain('(1)');
    fireEvent.click(btn);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith('DS-001', [mockSteps[0]]);
      expect(screen.getByTestId('sim-overall-status').textContent).toContain('MODERATE');
    });

    // Tabla de percentiles por columna
    const table = screen.getByTestId('sim-columns-table');
    expect(table.textContent).toContain('Salary');
    // P50 antes → después (formato de miles dependiente del locale del entorno)
    expect(table.textContent).toMatch(/74[.,]000/);
    expect(table.textContent).toMatch(/75[.,]000/);
    // Δ máx formateado con signo
    expect(table.textContent).toContain('+4.17%');
    // Nota de gobernanza visible
    expect(screen.getByTestId('sim-governance-note').textContent).toContain('SIMULACIÓN HIPOTÉTICA');
  });

  it('muestra errores de pasos inválidos sin romper la simulación', async () => {
    const simWithErrors: DriftSimulationResult = {
      ...mockSimulation,
      applied_steps: 0,
      step_outcomes: [
        { step_id: 'STEP-001', operation: 'drop_database', column: null, applied: false, rows_affected: 0, error: 'Operación no registrada' },
      ],
    };
    vi.spyOn(api, 'simulateDrift').mockResolvedValue(simWithErrors);

    render(
      <LanguageProvider>
        <DriftSimulator datasetId="DS-001" steps={[mockSteps[0]]} />
      </LanguageProvider>
    );
    fireEvent.click(screen.getByTestId('simulate-drift-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('sim-step-error-STEP-001').textContent).toContain('Operación no registrada');
    });
  });

  it('muestra el error de la API cuando la simulación falla', async () => {
    vi.spyOn(api, 'simulateDrift').mockRejectedValue(new Error('Dataset no encontrado'));

    render(
      <LanguageProvider>
        <DriftSimulator datasetId="DS-404" steps={[mockSteps[0]]} />
      </LanguageProvider>
    );
    fireEvent.click(screen.getByTestId('simulate-drift-btn'));

    await waitFor(() => {
      expect(screen.getByText(/Dataset no encontrado/i)).toBeInTheDocument();
    });
  });

  it('no renderiza nada sin datasetId', () => {
    const { container } = render(
      <LanguageProvider>
        <DriftSimulator datasetId={null} steps={mockSteps} />
      </LanguageProvider>
    );
    expect(container.innerHTML).toBe('');
  });
});
