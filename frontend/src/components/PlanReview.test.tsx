import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { PlanReview } from './PlanReview';
import { LanguageProvider } from '../context/LanguageContext';
import { DatasetMetadata, ProfilingReport, TransformationPlan } from '../types';

const mockMetadata: DatasetMetadata = {
  dataset_id: 'DS-test-01',
  filename: 'test_sample.csv',
  file_type: 'csv',
  size_bytes: 1024,
  row_count: 50,
  column_count: 3,
  columns: ['ID_Cliente', 'Nombre', 'Importe'],
  created_at: '2026-09-02T10:00:00Z',
  status: 'validated',
  warnings: [],
};

const mockProfiling: ProfilingReport = {
  dataset_id: 'DS-test-01',
  row_count: 50,
  column_count: 3,
  duplicates_count: 0,
  duplicates_percentage: 0,
  memory_estimate_bytes: 2048,
  generated_at: '2026-09-02T10:00:01Z',
  global_warnings: [],
  columns: [
    {
      column_name: 'ID_Cliente',
      inferred_type: 'text',
      semantic_hint: 'id',
      null_count: 0,
      null_percentage: 0,
      unique_count: 50,
      sample_values: ['CLI-001', 'CLI-002', 'CLI-003'],
      warnings: [],
    },
    {
      column_name: 'Nombre',
      inferred_type: 'text',
      semantic_hint: 'name',
      null_count: 2,
      null_percentage: 4,
      unique_count: 48,
      sample_values: [' Juan ', 'MARCOS', 'Ana'],
      warnings: [],
    },
    {
      column_name: 'Importe',
      inferred_type: 'numeric',
      semantic_hint: 'currency',
      null_count: 1,
      null_percentage: 2,
      unique_count: 40,
      sample_values: ['120.50 €', '$50.00', '10.00'],
      min_value: 10.0,
      max_value: 120.5,
      warnings: [],
    },
  ],
};

const mockPlan: TransformationPlan = {
  plan_id: 'PLAN-test-01',
  dataset_id: 'DS-test-01',
  summary: 'Plan de prueba para previsualización de esquemas',
  source: 'rules',
  created_at: '2026-09-02T10:00:02Z',
  steps: [
    {
      step_id: 'step_1',
      operation: 'trim_text',
      column: 'Nombre',
      parameters: {},
      reason: 'Eliminar espacios sobrantes',
      confidence: 0.95,
      risk: 'low',
      affected_rows_estimate: 2,
      status: 'proposed',
    },
    {
      step_id: 'step_2',
      operation: 'convert_numeric',
      column: 'Importe',
      parameters: { fill_strategy: 'mean' },
      reason: 'Estandarizar importes con divisas a numérico float64',
      confidence: 0.9,
      risk: 'medium',
      affected_rows_estimate: 50,
      status: 'proposed',
    },
  ],
};

describe('PlanReview Component — Schema Previews', () => {
  it('renders global schema preview button and toggles the projected schema table', () => {
    const handleExecute = vi.fn();
    render(
      <LanguageProvider>
        <PlanReview
          plan={mockPlan}
          onExecutePlan={handleExecute}
          executing={false}
          metadata={mockMetadata}
          profiling={mockProfiling}
        />
      </LanguageProvider>
    );

    // Botón global de previsualización presente con el número total de columnas
    const globalBtn = screen.getByTestId('preview-global-schema-btn');
    expect(globalBtn).toBeInTheDocument();
    expect(globalBtn).toHaveTextContent(/Previsualizar Esquema \(3\)/i);

    // Inicialmente el panel no está visible
    expect(screen.queryByTestId('global-schema-panel')).not.toBeInTheDocument();

    // Clic para abrir el panel
    fireEvent.click(globalBtn);
    expect(screen.getByTestId('global-schema-panel')).toBeInTheDocument();
    expect(screen.getByText(/Esquema Proyectado de Columnas/i)).toBeInTheDocument();

    // Comprobar presencia de las 3 columnas y sus estados proyectados
    expect(screen.getByText('ID_Cliente')).toBeInTheDocument();
    expect(screen.getByText('Sin cambios')).toBeInTheDocument(); // ID_Cliente no tiene pasos asignados

    expect(screen.getByText('Nombre')).toBeInTheDocument();
    expect(screen.getAllByText(/Modificada \(1\)/i)).toHaveLength(2); // Nombre e Importe tienen 1 transformación cada una

    expect(screen.getByText('Importe')).toBeInTheDocument();

    // Clic nuevamente para ocultar
    fireEvent.click(globalBtn);
    expect(screen.queryByTestId('global-schema-panel')).not.toBeInTheDocument();
  });

  it('renders per-step schema preview button and expands column details inline', () => {
    const handleExecute = vi.fn();
    render(
      <LanguageProvider>
        <PlanReview
          plan={mockPlan}
          onExecutePlan={handleExecute}
          executing={false}
          metadata={mockMetadata}
          profiling={mockProfiling}
        />
      </LanguageProvider>
    );

    // Botón de previsualización de esquema en el paso 1 (columna Nombre)
    const step1Btn = screen.getByTestId('preview-col-btn-step_1');
    expect(step1Btn).toBeInTheDocument();
    expect(step1Btn).toHaveTextContent(/Ver esquema/i);

    // Inicialmente el detalle de la columna no está desplegado
    expect(screen.queryByTestId('col-schema-details-step_1')).not.toBeInTheDocument();

    // Clic para desplegar
    fireEvent.click(step1Btn);
    expect(screen.getByTestId('col-schema-details-step_1')).toBeInTheDocument();
    expect(screen.getByText(/Detalles del Esquema: Nombre/i)).toBeInTheDocument();
    expect(screen.getByText(/2 \(4\.0%\)/i)).toBeInTheDocument(); // 2 nulos (4.0%)

    // Botón cambia su texto a Ocultar esquema
    expect(step1Btn).toHaveTextContent(/Ocultar esquema/i);

    // Clic para replegar
    fireEvent.click(step1Btn);
    expect(screen.queryByTestId('col-schema-details-step_1')).not.toBeInTheDocument();
  });

  it('allows approving and executing plan with steps', () => {
    const handleExecute = vi.fn();
    render(
      <LanguageProvider>
        <PlanReview
          plan={mockPlan}
          onExecutePlan={handleExecute}
          executing={false}
          metadata={mockMetadata}
          profiling={mockProfiling}
        />
      </LanguageProvider>
    );

    const execBtn = screen.getByTestId('execute-plan-btn');
    expect(execBtn).toBeInTheDocument();
    fireEvent.click(execBtn);

    expect(handleExecute).toHaveBeenCalledTimes(1);
    expect(handleExecute).toHaveBeenCalledWith(mockPlan.steps);
  });

  it('renders AI inference metrics banner when plan has ai_metrics', () => {
    const handleExecute = vi.fn();
    const planWithMetrics: TransformationPlan = {
      ...mockPlan,
      source: 'ai_copilot',
      ai_metrics: {
        latency_ms: 1240,
        prompt_tokens: 380,
        completion_tokens: 120,
        total_tokens: 500,
        estimated_cost_usd: 0.000086,
        model: 'gemini-2.5-flash',
        provider: 'gemini',
      },
    };

    render(
      <LanguageProvider>
        <PlanReview
          plan={planWithMetrics}
          onExecutePlan={handleExecute}
          executing={false}
          metadata={mockMetadata}
          profiling={mockProfiling}
        />
      </LanguageProvider>
    );

    const banner = screen.getByTestId('ai-metrics-banner');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent('gemini-2.5-flash');
    expect(banner).toHaveTextContent('1.24 s');
    expect(banner).toHaveTextContent('500');
    expect(banner).toHaveTextContent('$0.000086 USD');
  });

  it('renders ai-cached-badge when plan inference was served from cache', async () => {
    const handleExecute = vi.fn();
    const planWithCache: TransformationPlan = {
      ...mockPlan,
      source: 'ai_copilot',
      ai_metrics: {
        latency_ms: 0.5,
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
        estimated_cost_usd: 0.0,
        model: 'gemini-2.5-flash (cached)',
        provider: 'gemini',
        cached: true,
      },
    };

    render(
      <LanguageProvider>
        <PlanReview
          plan={planWithCache}
          onExecutePlan={handleExecute}
          executing={false}
          metadata={mockMetadata}
          profiling={mockProfiling}
        />
      </LanguageProvider>
    );

    const badge = screen.getByTestId('ai-cached-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/Caché de Inferencia/i);

    await act(async () => {
      fireEvent.click(badge);
    });
    expect(screen.getByTestId('cache-observability-modal')).toBeInTheDocument();
  });
});
