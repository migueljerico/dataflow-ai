import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PowerBiBuildGuide } from './PowerBiBuildGuide';
import { LanguageProvider } from '../context/LanguageContext';
import { DashboardBlueprint } from '../types';

/** Blueprint mínimo: la guía solo lee dax_measures y design.palette. */
const blueprint = {
  blueprint_id: 'dbp_guia001',
  name: 'Dashboard Ejecutivo',
  dax_measures: [
    { name: 'Total_Importe', formula: "SUM('Hechos'[Importe])", table_context: 'Hechos', purpose: 'Suma total', validated: true, kind: 'base' },
    { name: 'Margen_pct', formula: "[Margen] / [Total_Importe]", table_context: 'Hechos', purpose: 'Margen', validated: true, kind: 'ratio' },
  ],
  design: {
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
  },
} as unknown as DashboardBlueprint;

/** Blueprint completo: visuales por tipo, KPIs, filtros y preguntas de negocio. */
const richBlueprint = {
  blueprint_id: 'dbp_guia002',
  name: 'Dashboard Comercial',
  dax_measures: blueprint.dax_measures,
  kpis: [
    { kpi_id: 'kpi_1', title: 'Ventas netas', dax_measure_name: 'Ventas_netas', hidden: false },
    { kpi_id: 'kpi_2', title: 'Margen oculto', dax_measure_name: 'Margen_pct', hidden: true },
  ],
  visuals: [
    { visual_id: 'vis_1', title: 'Ventas por región', visual_type: 'bar', fields: ['Region', 'Ventas_netas'], hidden: false },
    { visual_id: 'vis_2', title: 'Ranking de productos', visual_type: 'horizontal_bar', fields: ['Producto', 'Ventas_netas'], hidden: false },
    { visual_id: 'vis_3', title: 'Precio frente a volumen', visual_type: 'scatter', fields: ['Precio', 'Unidades'], hidden: false },
    { visual_id: 'vis_4', title: 'Distribución de importes', visual_type: 'histogram', fields: ['Importe'], hidden: false },
    { visual_id: 'vis_5', title: 'Detalle de pedidos', visual_type: 'table', fields: ['Pedido', 'Importe'], hidden: false },
    { visual_id: 'vis_6', title: 'Serie oculta', visual_type: 'line', fields: ['Fecha'], hidden: true },
  ],
  filters: [
    { filter_id: 'flt_1', table_ref: 'Hechos', column: 'Fecha', label: 'Periodo', recommended_values: ['2024', '2025'], purpose: 'Acotar el ejercicio', order: 1, hidden: false },
  ],
  business_questions: [
    { question_id: 'q_1', text: '¿Cuáles son las ventas por región?' },
    { question_id: 'q_2', text: '¿Qué productos lideran el ranking?' },
  ],
  design: blueprint.design,
} as unknown as DashboardBlueprint;

const renderGuide = (bp: DashboardBlueprint = blueprint) =>
  render(
    <LanguageProvider>
      <PowerBiBuildGuide blueprint={bp} />
    </LanguageProvider>,
  );

describe('PowerBiBuildGuide — guía paso a paso para construir el Dashboard en Power BI', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renderiza los 8 pasos con sus rutas reales de la interfaz de Power BI (ES)', () => {
    renderGuide();

    expect(screen.getByTestId('powerbi-guide')).toBeInTheDocument();
    expect(screen.getByTestId('powerbi-guide-title')).toHaveTextContent('construye tu Dashboard en Power BI');

    for (let step = 1; step <= 8; step += 1) {
      expect(screen.getByTestId(`powerbi-guide-step-${step}`)).toBeInTheDocument();
      expect(screen.getByTestId(`powerbi-guide-step-${step}-badge`)).toHaveTextContent(String(step));
    }

    // Rutas verificadas contra la documentación oficial (identificadores técnicos)
    expect(screen.getByTestId('powerbi-guide-step-2-route')).toHaveTextContent('Modeling → New measure');
    expect(screen.getByTestId('powerbi-guide-step-3-route')).toHaveTextContent('Insertar → Elementos → Formas');
    expect(screen.getByTestId('powerbi-guide-step-4-route')).toHaveTextContent('Formato visual → General → Efectos');
    expect(screen.getByTestId('powerbi-guide-step-5-route')).toHaveTextContent('Panel Visualizaciones → icono KPI');
    expect(screen.getByTestId('powerbi-guide-step-6-route')).toHaveTextContent('Panel Visualizaciones → icono del tipo de visual');
    expect(screen.getByTestId('powerbi-guide-step-7-route')).toHaveTextContent('Panel Visualizaciones → icono Segmentación de datos (Slicer)');
    expect(screen.getByTestId('powerbi-guide-step-8-route')).toHaveTextContent('Inicio → Publicar');

    // Requisitos cubiertos: rectángulo, esquinas redondeadas, fondo sólido, DAX y KPI
    expect(screen.getByTestId('powerbi-guide-step-3')).toHaveTextContent('rectángulo');
    expect(screen.getByTestId('powerbi-guide-step-4')).toHaveTextContent('esquinas redondeadas');
    expect(screen.getByTestId('powerbi-guide-step-4')).toHaveTextContent('Transparencia al 0 %');
    expect(screen.getByTestId('powerbi-guide-step-2')).toHaveTextContent('tabla principal (home table)');
    expect(screen.getByTestId('powerbi-guide-step-5')).toHaveTextContent('Eje de tendencia');
    expect(screen.getByTestId('powerbi-guide-step-5')).toHaveTextContent('Destino');
    expect(screen.getByTestId('powerbi-guide-step-5-note')).toHaveTextContent('NULL');
  });

  it('personaliza la guía con las medidas DAX y la paleta reales del Blueprint', () => {
    renderGuide();

    const measures = screen.getByTestId('powerbi-guide-measures');
    expect(measures).toHaveTextContent('Total_Importe');
    expect(measures).toHaveTextContent('Margen_pct');

    const palette = screen.getByTestId('powerbi-guide-palette');
    expect(palette).toHaveTextContent('#0EA5E9');
    expect(palette).toHaveTextContent('#0F172A');
  });

  it('enseña una receta por cada tipo de visual propuesto en la pestaña Visuales', () => {
    renderGuide(richBlueprint);

    // Recetas por tipo (solo los tipos presentes y no ocultos)
    expect(screen.getByTestId('powerbi-guide-visual-recipe-bar')).toBeInTheDocument();
    expect(screen.getByTestId('powerbi-guide-visual-recipe-bar-route')).toHaveTextContent('Panel Visualizaciones → icono Gráfico de columnas agrupadas');
    expect(screen.getByTestId('powerbi-guide-visual-recipe-horizontal_bar-route')).toHaveTextContent('Gráfico de barras agrupadas');
    expect(screen.getByTestId('powerbi-guide-visual-recipe-scatter-route')).toHaveTextContent('Gráfico de dispersión');
    expect(screen.getByTestId('powerbi-guide-visual-recipe-histogram-route')).toHaveTextContent('Panel Datos → clic derecho en la columna → Nuevo grupo');
    expect(screen.getByTestId('powerbi-guide-visual-recipe-table-route')).toHaveTextContent('Panel Visualizaciones → icono Tabla');
    expect(screen.queryByTestId('powerbi-guide-visual-recipe-line')).toBeNull();

    // Los títulos y campos reales del Blueprint acompañan a cada receta
    const visuals = screen.getByTestId('powerbi-guide-visuals');
    expect(visuals).toHaveTextContent('Ventas por región');
    expect(visuals).toHaveTextContent('Region, Ventas_netas');
    expect(visuals).toHaveTextContent('Distribución de importes');
    expect(visuals).not.toHaveTextContent('Serie oculta');

    // Cada receta enlaza su artículo oficial de Microsoft Learn
    expect(screen.getByTestId('powerbi-guide-visual-recipe-bar-src').getAttribute('href')).toContain('/es-es/power-bi/visuals/power-bi-visualization-column-charts');
    expect(screen.getByTestId('powerbi-guide-visual-recipe-histogram-src').getAttribute('href')).toContain('/es-es/power-bi/create-reports/desktop-grouping-and-binning');
  });

  it('personaliza KPIs, filtros y preguntas de negocio del Blueprint', () => {
    renderGuide(richBlueprint);

    const kpis = screen.getByTestId('powerbi-guide-kpis');
    expect(kpis).toHaveTextContent('Ventas netas · Ventas_netas');
    expect(kpis).not.toHaveTextContent('Margen oculto');

    const filters = screen.getByTestId('powerbi-guide-filters');
    expect(filters).toHaveTextContent('Periodo');
    expect(filters).toHaveTextContent('Hechos.Fecha');
    expect(filters).toHaveTextContent('2024, 2025');

    const questions = screen.getByTestId('powerbi-guide-questions');
    expect(questions).toHaveTextContent('¿Cuáles son las ventas por región?');
    expect(questions).toHaveTextContent('¿Qué productos lideran el ranking?');
  });

  it('omite los bloques dinámicos cuando el Blueprint no propone ese contenido', () => {
    renderGuide();

    expect(screen.queryByTestId('powerbi-guide-visuals')).toBeNull();
    expect(screen.queryByTestId('powerbi-guide-filters')).toBeNull();
    expect(screen.queryByTestId('powerbi-guide-questions')).toBeNull();
    expect(screen.queryByTestId('powerbi-guide-kpis')).toBeNull();
  });

  it('enlaza la documentación oficial de Microsoft Learn con la variante localizada', () => {
    renderGuide();

    const sources = screen.getByTestId('powerbi-guide-sources');
    const links = sources.querySelectorAll('a');
    expect(links).toHaveLength(7);
    const hrefs = Array.from(links).map((a) => a.getAttribute('href'));
    expect(hrefs[0]).toContain('/es-es/power-bi/transform-model/desktop-measures');
    expect(hrefs[1]).toContain('/es-es/power-bi/create-reports/power-bi-reports-add-text-and-shapes');
    expect(hrefs[2]).toContain('/es-es/power-bi/visuals/power-bi-visualization-format-pane-overview');
    expect(hrefs[3]).toContain('/es-es/power-bi/visuals/power-bi-visualization-kpi');
    expect(hrefs[4]).toContain('/es-es/power-bi/visuals/power-bi-visualizations-overview');
    expect(hrefs[5]).toContain('/es-es/power-bi/visuals/power-bi-visualization-slicers');
    expect(hrefs[6]).toContain('/es-es/power-bi/collaborate-share/service-share-dashboards');
    for (const link of links) {
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
  });

  it('añade las fuentes de los tipos de visual presentes sin repetir enlaces', () => {
    renderGuide(richBlueprint);

    const links = Array.from(screen.getByTestId('powerbi-guide-sources').querySelectorAll('a'));
    const hrefs = links.map((a) => a.getAttribute('href'));
    expect(hrefs).toHaveLength(11);
    // bar, horizontal_bar y stacked_bar comparten el mismo artículo oficial
    expect(hrefs.filter((href) => href?.endsWith('power-bi-visualization-column-charts'))).toHaveLength(1);
    expect(hrefs.some((href) => href?.endsWith('power-bi-visualization-scatter'))).toBe(true);
    expect(hrefs.some((href) => href?.endsWith('desktop-grouping-and-binning'))).toBe(true);
    expect(hrefs.some((href) => href?.endsWith('power-bi-visualization-tables'))).toBe(true);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it('traduce la guía completa al inglés con la nota de verificación', () => {
    localStorage.setItem('dataflow_app_language', 'en');
    renderGuide(richBlueprint);

    expect(screen.getByTestId('powerbi-guide-title')).toHaveTextContent('build your Dashboard in Power BI');
    expect(screen.getByTestId('powerbi-guide-step-3')).toHaveTextContent('rectangle');
    expect(screen.getByTestId('powerbi-guide-step-4')).toHaveTextContent('Rounded corners');
    expect(screen.getByTestId('powerbi-guide-step-2-route')).toHaveTextContent('Modeling → New measure');
    expect(screen.getByTestId('powerbi-guide-step-6-route')).toHaveTextContent('Visualizations pane → visual type icon');
    expect(screen.getByTestId('powerbi-guide-step-7-route')).toHaveTextContent('Visualizations pane → Slicer icon');
    expect(screen.getByTestId('powerbi-guide-step-8-route')).toHaveTextContent('Home → Publish');
    expect(screen.getByTestId('powerbi-guide-source-note')).toHaveTextContent('official Microsoft Learn documentation');
    expect(screen.getByTestId('powerbi-guide-governance')).toHaveTextContent('AI proposes, the user decides');

    // Recetas y bloques traducidos al inglés
    expect(screen.getByTestId('powerbi-guide-visual-recipe-bar-route')).toHaveTextContent('Visualizations pane → Clustered column chart icon');
    expect(screen.getByTestId('powerbi-guide-visuals')).toHaveTextContent('Fields: Region, Ventas_netas');
    expect(screen.getByTestId('powerbi-guide-filters')).toHaveTextContent('Recommended values');
    expect(screen.getByTestId('powerbi-guide-step-8')).toHaveTextContent('Business questions');
    expect(screen.getByTestId('powerbi-guide-questions')).toHaveTextContent('¿Cuáles son las ventas por región?');

    const hrefs = Array.from(screen.getByTestId('powerbi-guide-sources').querySelectorAll('a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(hrefs[0]).toContain('/en-us/power-bi/transform-model/desktop-measures');
    expect(hrefs.some((href) => href?.includes('/en-us/power-bi/visuals/power-bi-visualization-column-charts'))).toBe(true);
  });
});
