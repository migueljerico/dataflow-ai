import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DashboardPreview } from './DashboardPreview';
import { LanguageProvider } from '../context/LanguageContext';
import { DashboardBlueprint } from '../types';

const PALETTE_ALT = {
  name: 'Ejecutivo (verde)',
  primary_color: '#059669',
  secondary_color: '#0D9488',
  accent_color: '#F59E0B',
  background_color: '#FFFFFF',
  text_color: '#0F172A',
  muted_text_color: '#475569',
  positive_color: '#059669',
  negative_color: '#E11D48',
  warning_color: '#B45309',
};

const buildBlueprint = (): DashboardBlueprint =>
  JSON.parse(
    JSON.stringify({
      blueprint_id: 'dbp_hitl1234567890',
      model_id: 'model_1',
      dataset_ids: ['ds1'],
      name: 'Rendimiento de Ventas',
      dashboard_type: 'sales',
      objective: 'Analizar las ventas con lectura ejecutiva.',
      audience: 'Dirección comercial',
      business_questions: [{ question_id: 'q_0', text: '¿Cuál es la evolución mensual?' }],
      pages: [
        {
          page_id: 'page_overview',
          title: 'Resumen ejecutivo',
          purpose: 'Lectura rápida',
          visual_ids: ['vis_line_fecha', 'vis_bar_zona'],
          layout_section: 'Header',
        },
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
        {
          visual_id: 'vis_bar_zona',
          title: 'Ventas por zona',
          visual_type: 'bar',
          page_id: 'page_overview',
          dimension: 'DimZona[Zona]',
          measure: 'Hechos[Importe]',
          measure_name: 'Ventas netas',
          fields: ['DimZona[Zona]', 'Hechos[Importe]'],
          axis_label: 'Zona',
          reason: 'Comparación directa.',
          confidence: 'high',
          confidence_rationale: 'base',
          alternative_types: ['horizontal_bar'],
          preview_data: [
            { label: 'Norte', value: 300 },
            { label: 'Sur', value: 150 },
          ],
          preview_mode: 'real',
          data_quality_notes: [],
          order: 1,
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
        {
          kpi_id: 'kpi_pedidos',
          title: 'Nº de pedidos',
          description: 'Conteo de pedidos.',
          dax_measure_name: 'Num_Pedidos',
          dax_formula: "COUNTROWS('Hechos')",
          table_context: 'Hechos',
          format_type: 'number',
          validated: true,
          value: 6,
          value_label: '6',
          confidence: 'high',
          data_quality_notes: [],
          order: 1,
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
        palette_variants: [PALETTE_ALT],
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
        visual_recommendation_count: 2,
        wcag_validation_failed: 0,
        deterministic: true,
      },
      created_at: '2026-09-22T00:00:00Z',
    })
  ) as DashboardBlueprint;

/** Harness con estado que replica el comportamiento de App.tsx (setDashboardBlueprint). */
const PreviewHarness: React.FC<{ initial: DashboardBlueprint; onUpdated: (b: DashboardBlueprint) => void }> = ({
  initial,
  onUpdated,
}) => {
  const [current, setCurrent] = React.useState(initial);
  return (
    <LanguageProvider>
      <DashboardPreview
        blueprint={current}
        onBlueprintUpdated={(b) => {
          setCurrent(b);
          onUpdated(b);
        }}
      />
    </LanguageProvider>
  );
};

const renderPreview = (blueprint: DashboardBlueprint, onBlueprintUpdated = vi.fn()) =>
  render(<PreviewHarness initial={blueprint} onUpdated={onBlueprintUpdated} />);

const mockFetchEcho = () =>
  vi.fn().mockImplementation(async (_url: string, init: RequestInit) => ({
    ok: true,
    status: 200,
    json: async () => JSON.parse(String(init.body)),
  }));

describe('DashboardPreview — edición HITL del Paso 5', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('abre el editor y guarda el nombre editado vía PUT con revalidación', async () => {
    const bp = buildBlueprint();
    const onUpdated = vi.fn();
    (globalThis as any).fetch = mockFetchEcho();
    renderPreview(bp, onUpdated);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));
    const input = screen.getByTestId('edit-name-input') as HTMLInputElement;
    expect(input.value).toBe('Rendimiento de Ventas');

    fireEvent.change(input, { target: { value: 'Ventas del Trimestre' } });
    fireEvent.click(screen.getByTestId('edit-save-btn'));

    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));
    const saved = onUpdated.mock.calls[0][0] as DashboardBlueprint;
    expect(saved.name).toBe('Ventas del Trimestre');
    expect((globalThis as any).fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (globalThis as any).fetch.mock.calls[0];
    expect(String(url)).toContain('/api/v1/dashboard/dbp_hitl1234567890');
    expect(init.method).toBe('PUT');
    // Tras guardar se vuelve a la vista de solo lectura
    expect(screen.queryByTestId('dashboard-editor')).not.toBeInTheDocument();
    expect(screen.getByTestId('blueprint-title')).toHaveTextContent('Ventas del Trimestre');
  });

  it('permite ocultar un KPI y reordenarlo antes de guardar', async () => {
    const bp = buildBlueprint();
    const onUpdated = vi.fn();
    (globalThis as any).fetch = mockFetchEcho();
    renderPreview(bp, onUpdated);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));

    // Ocultar el primer KPI (la propuesta de la IA se conserva, solo se oculta)
    const hideBtn = screen.getByRole('button', { name: 'Ocultar: Total importe' });
    fireEvent.click(hideBtn);
    expect(screen.getByRole('button', { name: 'Mostrar: Total importe' })).toBeInTheDocument();

    // Bajar el primer KPI: pasa después del segundo
    fireEvent.click(screen.getByRole('button', { name: 'Bajar: Total importe' }));
    const kpiRows = screen.getAllByTestId(/^edit-kpi-/);
    expect(kpiRows[0]).toHaveAttribute('data-testid', 'edit-kpi-kpi_pedidos');

    fireEvent.click(screen.getByTestId('edit-save-btn'));
    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));
    const saved = onUpdated.mock.calls[0][0] as DashboardBlueprint;
    expect(saved.kpis[0].kpi_id).toBe('kpi_pedidos');
    const hiddenKpi = saved.kpis.find((k) => k.kpi_id === 'kpi_total');
    expect(hiddenKpi?.hidden).toBe(true);
  });

  it('solo ofrece tipos de visual prevalidados (alternativas del blueprint)', () => {
    const bp = buildBlueprint();
    renderPreview(bp);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));
    const select = screen.getByTestId('edit-visual-type-vis_line_fecha') as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toEqual(['line', 'area']);

    fireEvent.change(select, { target: { value: 'area' } });
    expect(select.value).toBe('area');
  });

  it('permite cambiar la paleta por una variante WCAG y actualiza los swatches', () => {
    const bp = buildBlueprint();
    renderPreview(bp);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));
    const paletteSelect = screen.getByTestId('edit-palette-select') as HTMLSelectElement;
    expect(Array.from(paletteSelect.options).map((o) => o.textContent)).toEqual([
      'Analítico moderno (azul) ✓',
      'Ejecutivo (verde)',
    ]);

    fireEvent.change(paletteSelect, { target: { value: '1' } });
    expect(screen.getByTestId('palette-swatch-Primario')).toHaveTextContent('#059669');
  });

  it('descartar cambios restaura la vista de solo lectura sin llamar al backend', () => {
    const bp = buildBlueprint();
    const onUpdated = vi.fn();
    (globalThis as any).fetch = vi.fn();
    renderPreview(bp, onUpdated);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));
    fireEvent.change(screen.getByTestId('edit-name-input'), { target: { value: 'Nombre temporal' } });
    fireEvent.click(screen.getByTestId('edit-cancel-btn'));

    expect(screen.queryByTestId('dashboard-editor')).not.toBeInTheDocument();
    expect(screen.getByTestId('blueprint-title')).toHaveTextContent('Rendimiento de Ventas');
    expect(onUpdated).not.toHaveBeenCalled();
    expect((globalThis as any).fetch).not.toHaveBeenCalled();
  });

  it('muestra el error del backend y mantiene el editor si el guardado falla', async () => {
    const bp = buildBlueprint();
    const onUpdated = vi.fn();
    (globalThis as any).fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ message: 'Blueprint inválido' }),
    });
    renderPreview(bp, onUpdated);

    fireEvent.click(screen.getByTestId('edit-blueprint-btn'));
    fireEvent.click(screen.getByTestId('edit-save-btn'));

    await waitFor(() => expect(screen.getByTestId('editor-save-error')).toHaveTextContent('Blueprint inválido'));
    expect(screen.getByTestId('dashboard-editor')).toBeInTheDocument();
    expect(onUpdated).not.toHaveBeenCalled();
  });

  it('la vista de solo lectura no muestra KPIs ni visuales ocultos por el usuario', () => {
    const bp = buildBlueprint();
    bp.kpis[0].hidden = true;
    bp.visuals[0].hidden = true;
    renderPreview(bp);

    fireEvent.click(screen.getByRole('button', { name: /Resumen/i }));
    expect(screen.queryByText('Total importe')).not.toBeInTheDocument();
    expect(screen.getByText('Nº de pedidos')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Visuales/i }));
    expect(screen.queryByText('Evolución de Ventas por mes')).not.toBeInTheDocument();
    expect(screen.getByText('Ventas por zona')).toBeInTheDocument();
  });
});
