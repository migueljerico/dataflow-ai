import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DashboardPreview } from './DashboardPreview';
import { LanguageProvider } from '../context/LanguageContext';
import { DashboardBlueprint } from '../types';

const mockBlueprint = {
  blueprint_id: 'dbp_test1234567890',
  model_id: 'model_1',
  dataset_ids: ['ds1'],
  name: 'Rendimiento de Ventas — Prueba',
  dashboard_type: 'sales',
  objective: 'Analizar las ventas con lectura ejecutiva.',
  audience: 'Dirección comercial',
  business_questions: [{ question_id: 'q_0', text: '¿Cuál es la evolución mensual?' }],
  pages: [{ page_id: 'page_overview', title: 'Resumen ejecutivo', purpose: 'Lectura rápida', visual_ids: ['vis_line_fecha'], layout_section: 'Header' }],
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
        { label: '2024-03', value: 150 },
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
    {
      visual_id: 'vis_table_top',
      title: 'Top zona por Ventas',
      visual_type: 'table',
      page_id: 'page_detail',
      dimension: 'DimZona[Zona]',
      measure: 'Hechos[Importe]',
      measure_name: 'Ventas netas',
      fields: ['DimZona[Zona]', 'Hechos[Importe]'],
      reason: 'Detalle exacto.',
      confidence: 'high',
      confidence_rationale: 'base',
      alternative_types: [],
      preview_data: [{ label: 'Norte', value: 300 }],
      preview_mode: 'real',
      data_quality_notes: [],
      order: 2,
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
  power_bi_implementation: [
    {
      page: 'Resumen ejecutivo',
      visual: 'Evolución de Ventas por mes',
      visual_type: 'line',
      formatting: 'Ejes legibles.',
      accessibility: 'Texto alternativo.',
    },
  ],
  power_bi_summary: '1 instrucciones de visual, 1 medidas DAX y 1 slicers.',
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
    visual_recommendation_count: 3,
    wcag_validation_failed: 0,
    deterministic: true,
  },
  created_at: '2026-09-08T00:00:00Z',
} as unknown as DashboardBlueprint;

const renderPreview = () =>
  render(
    <LanguageProvider>
      <DashboardPreview blueprint={mockBlueprint} />
    </LanguageProvider>
  );

describe('DashboardPreview — pestaña Ejemplo con maqueta PNG', () => {
  it('muestra la maqueta de ejemplo por defecto con el botón de descarga PNG', () => {
    renderPreview();
    expect(screen.getByTestId('dashboard-mockup')).toBeInTheDocument();
    expect(screen.getByTestId('export-dashboard-mockup-png-btn')).toBeInTheDocument();
    expect(screen.getByTestId('export-dashboard-mockup-png-btn')).toHaveTextContent(/Descargar ejemplo PNG/i);
  });

  it('la maqueta incluye los KPIs reales del Blueprint y el título del dashboard', () => {
    renderPreview();
    // El SVG de la maqueta (role="img"); el primer <svg> del árbol es un icono de lucide
    const svg = screen.getByRole('img', { name: /Ejemplo visual del dashboard/i });
    expect(svg).toBeInTheDocument();
    expect(svg.textContent).toContain('Rendimiento de Ventas');
    expect(svg.textContent).toContain('450,00');
    expect(svg.textContent).toContain('Total_Importe');
  });

  it('permite cambiar a la pestaña Resumen y volver a Ejemplo', () => {
    renderPreview();
    fireEvent.click(screen.getByRole('button', { name: /Resumen/i }));
    expect(screen.getByText(/KPIs Recomendados/i)).toBeInTheDocument();
    expect(screen.queryByTestId('dashboard-mockup')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Ejemplo/i }));
    expect(screen.getByTestId('dashboard-mockup')).toBeInTheDocument();
  });

  it('el botón de descarga no rompe la app aunque el navegador no soporte canvas (try/catch)', () => {
    renderPreview();
    const btn = screen.getByTestId('export-dashboard-mockup-png-btn');
    fireEvent.click(btn);
    // La maqueta sigue visible tras el intento de exportación
    expect(screen.getByTestId('dashboard-mockup')).toBeInTheDocument();
  });
});
