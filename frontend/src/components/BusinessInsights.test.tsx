import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BusinessInsights } from './BusinessInsights';
import { LanguageProvider } from '../context/LanguageContext';
import { api } from '../services/api';
import { ExecutiveAnalyticsReport } from '../types';

const mockReport: ExecutiveAnalyticsReport = {
  run_id: 'run-test-123',
  dataset_name: 'test_clean.csv',
  domain: 'sales',
  kpis: [
    {
      id: 'kpi-rev',
      title: 'Facturación Total Estimada',
      value: '15.250,00 €',
      numeric_value: 15250.0,
      subtitle: 'Ventas brutas calculadas',
      category: 'financiero',
    },
    {
      id: 'kpi-tx',
      title: 'Transacciones Validadas',
      value: '120 pedidos',
      numeric_value: 120.0,
      subtitle: 'Registros únicos limpios',
      category: 'operaciones',
    },
  ],
  executive_summary: 'Resumen ejecutivo de prueba para ventas comerciales.',
  strategic_recommendations: ['Fomentar cross-selling en tienda online.'],
  category_breakdown: [
    {
      category_name: 'Web',
      count: 80,
      percentage: 66.7,
    },
    {
      category_name: 'Tienda',
      count: 40,
      percentage: 33.3,
    },
  ],
  cluster_visualization: {
    cluster_column: 'cluster_id',
    x_column: 'Precio_Unidad',
    y_column: 'Cantidad',
    available_numeric_columns: ['Precio_Unidad', 'Cantidad', 'Descuento'],
    total_points: 2,
    clusters: [
      {
        cluster_id: 0,
        label: 'Cluster 0',
        count: 1,
        percentage: 50.0,
        center_x: 100.0,
        center_y: 2.0,
        feature_averages: { Precio_Unidad: 100.0, Cantidad: 2.0, Descuento: 5.0 },
      },
      {
        cluster_id: 1,
        label: 'Cluster 1',
        count: 1,
        percentage: 50.0,
        center_x: 500.0,
        center_y: 10.0,
        feature_averages: { Precio_Unidad: 500.0, Cantidad: 10.0, Descuento: 15.0 },
      },
    ],
    points: [
      { row_index: 0, x: 100.0, y: 2.0, cluster_id: 0, label: 'Fila #1' },
      { row_index: 1, x: 500.0, y: 10.0, cluster_id: 1, label: 'Fila #2' },
    ],
  },
  outlier_visualization: {
    columns: [
      {
        column: 'Precio_Unidad',
        min: 20.0,
        q1: 50.0,
        median: 100.0,
        q3: 200.0,
        max: 1200.0,
        lower_whisker: 20.0,
        upper_whisker: 425.0,
        iqr: 150.0,
        mean: 180.0,
        std: 210.0,
        outliers_count: 1,
        outlier_percentage: 10.0,
        sample_outliers: [1200.0],
      },
      {
        column: 'Cantidad',
        min: 1.0,
        q1: 1.0,
        median: 2.0,
        q3: 3.0,
        max: 10.0,
        lower_whisker: 1.0,
        upper_whisker: 6.0,
        iqr: 2.0,
        mean: 2.5,
        std: 2.1,
        outliers_count: 1,
        outlier_percentage: 10.0,
        sample_outliers: [10.0],
      },
    ],
    active_column: 'Precio_Unidad',
    scatter_points: [
      { row_index: 0, x_value: 1, y_value: 100.0, is_outlier: false, label: 'Fila #1' },
      { row_index: 1, x_value: 2, y_value: 1200.0, is_outlier: true, label: 'Fila #2' },
    ],
    total_outliers_detected: 2,
    detection_method: 'IQR (1.5x) / Z-Score (>3.0)',
  },
};

describe('BusinessInsights component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading state initially and then displays KPIs and executive summary', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(mockReport);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-test-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
      expect(screen.getByText('15.250,00 €')).toBeInTheDocument();
      expect(screen.getByText('Resumen ejecutivo de prueba para ventas comerciales.')).toBeInTheDocument();
    });
  });

  it('allows switching to clusters tab and displays 2D scatter plot and cluster summary', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(mockReport);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-test-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    // Cambiar a pestaña de clusters
    const clustersTab = screen.getByRole('tab', { name: /Segmentación de Clusters/i });
    fireEvent.click(clustersTab);

    expect(screen.getByText(/Diagrama de Dispersión 2D de Clusters/i)).toBeInTheDocument();
    expect(screen.getByText('Columna: cluster_id')).toBeInTheDocument();
    expect(screen.getByText('2 Clusters')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Scatter Plot 2D de clusters/i })).toBeInTheDocument();
  });

  it('allows switching to outliers tab, displays BoxPlot and switches to scatter view', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(mockReport);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-test-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    // Cambiar a pestaña de outliers
    const outliersTab = screen.getByRole('tab', { name: /Detección de Outliers/i });
    fireEvent.click(outliersTab);

    expect(screen.getByText(/Distribución y Detección de Valores Atípicos/i)).toBeInTheDocument();
    expect(screen.getByText(/2 Outliers Detectados/i)).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Boxplot de Precio_Unidad/i })).toBeInTheDocument();

    // Cambiar a modo dispersión
    const scatterBtn = screen.getByRole('button', { name: /Dispersión/i });
    fireEvent.click(scatterBtn);

    expect(screen.getByRole('img', { name: /Scatter de outliers para Precio_Unidad/i })).toBeInTheDocument();
  });

  it('renders error message when API fails', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockRejectedValue(new Error('Fallo al conectar con el servidor'));

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-err" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Fallo al conectar con el servidor')).toBeInTheDocument();
    });
  });

  it('renders executive report export button and allows switching to Power BI / Excel integration tab', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(mockReport);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-test-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    // Verificar botón de exportación
    const exportBtn = screen.getByRole('link', { name: /Exportar Reporte Ejecutivo/i });
    expect(exportBtn).toBeInTheDocument();
    expect(exportBtn).toHaveAttribute('href', expect.stringContaining('/api/v1/analytics/run-test-123/export?lang=es'));

    // Cambiar a pestaña de Integración Power BI / Excel
    const integrationTab = screen.getByRole('tab', { name: /Integración Power BI \/ Excel/i });
    fireEvent.click(integrationTab);

    expect(screen.getByText(/Guía de Integración y Fórmulas para Power BI y Excel/i)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft Power BI/i)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft Excel/i)).toBeInTheDocument();
    expect(screen.getByText(/Total_Registros = COUNTROWS/i)).toBeInTheDocument();
  });
});
