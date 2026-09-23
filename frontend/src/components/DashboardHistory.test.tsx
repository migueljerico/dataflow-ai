import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DashboardPreview } from './DashboardPreview';
import { LanguageProvider } from '../context/LanguageContext';
import { DashboardBlueprint } from '../types';

const buildBlueprint = (): DashboardBlueprint =>
  JSON.parse(
    JSON.stringify({
      blueprint_id: 'dbp_test1234567890',
      model_id: 'model_1',
      dataset_ids: ['ds1'],
      name: 'Rendimiento de Ventas — Prueba',
      dashboard_type: 'sales',
      objective: 'Analizar las ventas con lectura ejecutiva.',
      audience: 'Dirección comercial',
      business_questions: [{ question_id: 'q_0', text: '¿Cuál es la evolución mensual?' }],
      pages: [
        { page_id: 'page_overview', title: 'Resumen ejecutivo', purpose: 'Lectura rápida', visual_ids: ['vis_line_fecha'], layout_section: 'Header' },
      ],
      visuals: [
        {
          visual_id: 'vis_line_fecha',
          title: 'Evolución de Ventas por mes',
          visual_type: 'line',
          page_id: 'page_overview',
          dimension: 'Hechos[Fecha]',
          measure: 'Hechos[Importe]',
          measure_name: 'Ventas netas',
          fields: ['Hechos[Fecha]', 'Hechos[Importe]'],
          axis_label: 'Fecha',
          reason: 'Tendencia continua.',
          confidence: 'high',
          confidence_rationale: 'base',
          alternative_types: ['area'],
          preview_data: [
            { label: '2024-01', value: 100 },
            { label: '2024-02', value: 200 },
          ],
          preview_mode: 'real',
          data_quality_notes: [],
          order: 0,
        },
      ],
      kpis: [
        {
          kpi_id: 'kpi_total',
          title: 'Total importe',
          description: 'Suma total.',
          dax_measure_name: 'Total_Importe',
          dax_formula: "SUM('Hechos'[Importe])",
          table_context: 'Hechos',
          format_type: 'currency',
          validated: true,
          value: 450,
          value_label: '450,00 €',
          confidence: 'high',
          data_quality_notes: [],
          order: 0,
        },
      ],
      filters: [
        {
          filter_id: 'filter_zona',
          table_ref: 'DimZona',
          column: 'Zona',
          label: 'Zona',
          recommended_values: ['Norte', 'Sur'],
          purpose: 'Acotar visuales.',
          order: 0,
        },
      ],
      hierarchies: [],
      design: {
        style: {
          style_name: 'Modern analytical',
          canvas: '16:9',
          layout: '12-column grid',
          spacing: '8px base grid',
          cards: 'Moderate radius',
          typography: 'Jerarquía clara',
          density: 'Medium',
          color_strategy: 'Base neutra',
          notes: [],
        },
        style_variants: [],
        palette: {
          name: 'Analítico moderno (azul)',
          primary_color: '#0EA5E9',
          secondary_color: '#3B82F6',
          accent_color: '#10B981',
          background_color: '#0F172A',
          text_color: '#F8FAFC',
          muted_text_color: '#94A3B8',
          positive_color: '#10B981',
          negative_color: '#F43F5E',
          warning_color: '#F59E0B',
        },
        palette_variants: [],
        accessibility: {
          contrast_pairs: [],
          checklist: [{ label: 'Contraste', status: 'pass', detail: 'OK' }],
          overall_label: 'WCAG AA: PASS',
          declarations: [],
        },
      },
      dax_measures: [
        { name: 'Total_Importe', formula: "SUM('Hechos'[Importe])", table_context: 'Hechos', purpose: 'Suma total', validated: true, kind: 'base' },
      ],
      power_bi_implementation: [],
      power_bi_summary: 'Guía de implementación.',
      semantic_model: {},
      data_quality: [],
      warnings: [],
      limitations: [],
      confidence: 'high',
      confidence_rationale: 'Reglas deterministas.',
      validation: { checks: [], passed_count: 18, total_count: 18, status: 'valid', issues: [] },
      generation_meta: {
        duration_ms: 42,
        dashboard_generation_total: 1,
        dashboard_generation_failed: 0,
        dashboard_validation_failed: 0,
        visual_recommendation_count: 1,
        wcag_validation_failed: 0,
        deterministic: true,
      },
      created_at: '2026-09-08T00:00:00Z',
    })
  ) as DashboardBlueprint;

const summary = (overrides: Record<string, unknown> = {}) => ({
  blueprint_id: 'dbp_hist9999999999',
  name: 'Propuesta Archivada',
  dashboard_type: 'sales',
  objective: 'Histórico de propuestas.',
  confidence: 'high',
  validation_status: 'valid',
  passed_count: 18,
  total_count: 18,
  dataset_ids: ['ds1'],
  kpi_count: 2,
  visual_count: 3,
  palette_name: 'Analítico moderno (azul)',
  created_at: '2026-09-01T10:00:00Z',
  ...overrides,
});

const historyList = (items: unknown[]) => ({ items, total: items.length, retention_days: 30 });

const jsonResponse = (payload: unknown) => ({
  ok: true,
  status: 200,
  json: async () => payload,
});

const PreviewHarness: React.FC<{ onLoaded: (b: DashboardBlueprint) => void }> = ({ onLoaded }) => (
  <LanguageProvider>
    <DashboardPreview blueprint={buildBlueprint()} onBlueprintLoad={onLoaded} />
  </LanguageProvider>
);

describe('DashboardPreview — historial y export TMDL/PBIP (Paso 5, v1.25.0)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('lista las propuestas del historial y marca la actual con la retención vigente', async () => {
    const onLoaded = vi.fn();
    (globalThis as any).fetch = vi.fn().mockImplementation(async (url: string) =>
      String(url).endsWith('/dashboard')
        ? jsonResponse(historyList([summary({ blueprint_id: 'dbp_test1234567890', name: 'Propuesta Actual' })]))
        : jsonResponse({})
    );
    render(<PreviewHarness onLoaded={onLoaded} />);

    fireEvent.click(screen.getByTestId('history-btn'));
    await waitFor(() => expect(screen.getByTestId('history-panel')).toBeInTheDocument());

    const item = await screen.findByTestId('history-item-dbp_test1234567890');
    expect(item).toHaveTextContent('Propuesta Actual');
    expect(item).toHaveTextContent('2 KPIs');
    expect(screen.getByTestId('history-current-mark')).toHaveTextContent('Actual');
    expect(screen.getByTestId('history-panel')).toHaveTextContent('Retención: 30 días');
    expect(onLoaded).not.toHaveBeenCalled();
  });

  it('carga una propuesta del historial en el preview vía onBlueprintLoad', async () => {
    const onLoaded = vi.fn();
    const archived = { ...buildBlueprint(), blueprint_id: 'dbp_hist9999999999', name: 'Blueprint Cargado del Historial' };
    (globalThis as any).fetch = vi.fn().mockImplementation(async (url: string) => {
      const target = String(url);
      if (target.endsWith('/dashboard')) return jsonResponse(historyList([summary()]));
      if (target.includes('/dashboard/dbp_hist9999999999')) return jsonResponse(archived);
      return jsonResponse({});
    });
    render(<PreviewHarness onLoaded={onLoaded} />);

    fireEvent.click(screen.getByTestId('history-btn'));
    const loadBtn = await screen.findByTestId('history-load-dbp_hist9999999999');
    fireEvent.click(loadBtn);

    await waitFor(() => expect(onLoaded).toHaveBeenCalledTimes(1));
    const loaded = onLoaded.mock.calls[0][0] as DashboardBlueprint;
    expect(loaded.blueprint_id).toBe('dbp_hist9999999999');
    await waitFor(() => expect(screen.queryByTestId('history-panel')).not.toBeInTheDocument());
  });

  it('muestra el error del historial sin cerrar el panel si el backend falla', async () => {
    const onLoaded = vi.fn();
    (globalThis as any).fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ message: 'Fallo de almacenamiento' }),
    });
    render(<PreviewHarness onLoaded={onLoaded} />);

    fireEvent.click(screen.getByTestId('history-btn'));
    await waitFor(() => expect(screen.getByTestId('history-error')).toHaveTextContent('Fallo de almacenamiento'));
    expect(screen.getByTestId('history-panel')).toBeInTheDocument();
    expect(onLoaded).not.toHaveBeenCalled();
  });

  it('la pestaña Power BI ofrece exportar el blueprint a TMDL y .pbip', async () => {
    const onLoaded = vi.fn();
    render(<PreviewHarness onLoaded={onLoaded} />);

    fireEvent.click(screen.getByRole('button', { name: /Power BI/i }));
    expect(screen.getByTestId('export-model-card')).toBeInTheDocument();

    const tmdl = screen.getByTestId('export-tmdl-btn') as HTMLAnchorElement;
    const pbip = screen.getByTestId('export-pbip-btn') as HTMLAnchorElement;
    expect(tmdl.getAttribute('href')).toBe('/api/v1/dashboard/dbp_test1234567890/export/tmdl');
    expect(pbip.getAttribute('href')).toBe('/api/v1/dashboard/dbp_test1234567890/export/pbip');
    expect((globalThis as any).fetch).not.toHaveBeenCalled();
  });
});
