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

const renderGuide = () =>
  render(
    <LanguageProvider>
      <PowerBiBuildGuide blueprint={blueprint} />
    </LanguageProvider>,
  );

describe('PowerBiBuildGuide — guía paso a paso para construir el Dashboard en Power BI', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renderiza los 5 pasos con sus rutas reales de la interfaz de Power BI (ES)', () => {
    renderGuide();

    expect(screen.getByTestId('powerbi-guide')).toBeInTheDocument();
    expect(screen.getByTestId('powerbi-guide-title')).toHaveTextContent('construye tu Dashboard en Power BI');

    for (let step = 1; step <= 5; step += 1) {
      expect(screen.getByTestId(`powerbi-guide-step-${step}`)).toBeInTheDocument();
      expect(screen.getByTestId(`powerbi-guide-step-${step}-badge`)).toHaveTextContent(String(step));
    }

    // Rutas verificadas contra la documentación oficial (identificadores técnicos)
    expect(screen.getByTestId('powerbi-guide-step-2-route')).toHaveTextContent('Modeling → New measure');
    expect(screen.getByTestId('powerbi-guide-step-3-route')).toHaveTextContent('Insertar → Elementos → Formas');
    expect(screen.getByTestId('powerbi-guide-step-4-route')).toHaveTextContent('Formato visual → General → Efectos');
    expect(screen.getByTestId('powerbi-guide-step-5-route')).toHaveTextContent('Panel Visualizaciones → icono KPI');

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

  it('enlaza la documentación oficial de Microsoft Learn con la variante localizada', () => {
    renderGuide();

    const sources = screen.getByTestId('powerbi-guide-sources');
    const links = sources.querySelectorAll('a');
    expect(links).toHaveLength(4);
    const hrefs = Array.from(links).map((a) => a.getAttribute('href'));
    expect(hrefs[0]).toContain('/es-es/power-bi/transform-model/desktop-measures');
    expect(hrefs[1]).toContain('/es-es/power-bi/create-reports/power-bi-reports-add-text-and-shapes');
    expect(hrefs[2]).toContain('/es-es/power-bi/visuals/power-bi-visualization-format-pane-overview');
    expect(hrefs[3]).toContain('/es-es/power-bi/visuals/power-bi-visualization-kpi');
    for (const link of links) {
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
  });

  it('traduce la guía completa al inglés con la nota de verificación', () => {
    localStorage.setItem('dataflow_app_language', 'en');
    renderGuide();

    expect(screen.getByTestId('powerbi-guide-title')).toHaveTextContent('build your Dashboard in Power BI');
    expect(screen.getByTestId('powerbi-guide-step-3')).toHaveTextContent('rectangle');
    expect(screen.getByTestId('powerbi-guide-step-4')).toHaveTextContent('Rounded corners');
    expect(screen.getByTestId('powerbi-guide-step-2-route')).toHaveTextContent('Modeling → New measure');
    expect(screen.getByTestId('powerbi-guide-source-note')).toHaveTextContent('official Microsoft Learn documentation');
    expect(screen.getByTestId('powerbi-guide-governance')).toHaveTextContent('AI proposes, the user decides');

    const hrefs = Array.from(screen.getByTestId('powerbi-guide-sources').querySelectorAll('a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(hrefs[0]).toContain('/en-us/power-bi/transform-model/desktop-measures');
  });
});
