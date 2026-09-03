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
      { row_index: 0, x_value: 1, y_value: 100.0, is_outlier: false, label: 'Fila #1', raw_y_value: 100.0, was_modified: false, diff_status: 'unchanged' },
      { row_index: 1, x_value: 2, y_value: 425.0, is_outlier: false, label: 'Fila #2', raw_y_value: 1200.0, was_modified: true, diff_status: 'resolved_outlier' },
    ],
    diff_summary: {
      raw_outliers_count: 2,
      clean_outliers_count: 0,
      resolved_outliers_count: 2,
      reduction_percentage: 100.0,
    },
    total_outliers_detected: 2,
    detection_method: 'IQR (1.5x) / Z-Score (>3.0)',
  },
  drift_analysis: {
    overall_drift_status: 'stable',
    stable_columns_count: 1,
    moderate_columns_count: 0,
    critical_columns_count: 0,
    total_alerts: 1,
    alerts: [],
    generated_at: '2026-09-03T12:00:00Z',
    global_recommendations: [
      {
        id: 'rec_01',
        priority: 'medium',
        category: 'capping',
        action_type: 'capping',
        title: 'Acotar valores atípicos en Precio_Unidad',
        rationale: 'Se detectaron outliers leves en la cola superior P95.',
        column: 'Precio_Unidad',
        suggested_step: 'cap_outliers(column="Precio_Unidad", method="iqr")',
      },
    ],
    columns: [
      {
        column_name: 'Precio_Unidad',
        drift_score: 4.2,
        drift_status: 'stable',
        ks_statistic: 0.042,
        raw_percentiles: {
          min_val: 5.0,
          max_val: 600.0,
          p05: 10.0,
          p25: 50.0,
          p50: 100.0,
          p75: 200.0,
          p95: 500.0,
          mean: 150.0,
          std: 120.0,
          iqr: 150.0,
        },
        clean_percentiles: {
          min_val: 5.0,
          max_val: 550.0,
          p05: 10.0,
          p25: 50.0,
          p50: 100.0,
          p75: 200.0,
          p95: 500.0,
          mean: 150.0,
          std: 120.0,
          iqr: 150.0,
        },
        shift: {
          p05_shift_pct: 0.0,
          p25_shift_pct: 0.0,
          p50_shift_pct: 0.0,
          p75_shift_pct: 0.0,
          p95_shift_pct: 0.0,
          max_shift_pct: 0.0,
        },
        anomaly_count: 1,
        anomaly_percentage: 1.2,
        alerts: [
          {
            id: 'alt_01',
            severity: 'info',
            title: 'Anomalías Leves',
            message: '1 anomalías detectadas en Precio_Unidad',
            column: 'Precio_Unidad',
            metric: 'anomaly_rate',
            value: 1.2,
            threshold: 5.0,
          },
        ],
        recommendations: [],
      },
    ],
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

    // Cambiar a modo comparador diff (Crudo vs Limpio)
    const diffBtn = screen.getByRole('button', { name: /Comparador Diff/i });
    fireEvent.click(diffBtn);

    expect(screen.getByTestId('outlier-diff-container')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Comparador scatter diff para Precio_Unidad/i })).toBeInTheDocument();
    expect(screen.getByText(/Anomalías Resueltas/i)).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByTestId('toggle-diff-modified-btn')).toBeInTheDocument();
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

  it('renders adaptive integration guide with dynamic DAX and Excel formulas when available', async () => {
    const reportWithGuide: ExecutiveAnalyticsReport = {
      ...mockReport,
      integration_guide: {
        table_name: 'Ventas_Comerciales',
        clean_filename: 'Ventas_Comerciales.csv',
        parquet_filename: 'Ventas_Comerciales.parquet',
        power_query_m_csv: 'let\n    Source = Csv.Document(...)\nin\n    #"Changed Type"',
        power_query_m_parquet: 'let\n    Source = Parquet.Document(...)\nin\n    #"Changed Type"',
        tmdl_table_definition: "table Ventas_Comerciales\n\tlineageTag: 12345\n\n\tmeasure 'Total_Ventas' = SUM('Ventas_Comerciales'[Ventas])",
        dax_measures: [
          {
            name: 'Total_Ventas',
            formula: "Total_Ventas = SUM('Ventas_Comerciales'[Ventas])",
            description: "Suma total de la métrica 'Ventas'.",
            category: 'numerico',
            format_string: '#,##0.00 €',
            display_folder: 'KPIs Directivos',
          },
        ],
        excel_formulas: [
          {
            title: 'Validación IQR Outliers — Ventas',
            column: 'Ventas',
            formula_es: '=SI(ESNUMERO(C2); "OK"; "Outlier")',
            formula_en: '=IF(ISNUMBER(C2), "OK", "Outlier")',
            excel_column_letter: 'C',
            description: 'Validación de outliers para Ventas.',
            category: 'outlier',
            target_cell: 'C2',
          },
          {
            title: 'Total Suma — Ventas',
            column: 'Ventas',
            formula_es: '=SUMA(C2:C1501)',
            formula_en: '=SUM(C2:C1501)',
            excel_column_letter: 'C',
            description: 'Suma acumulada de Ventas.',
            category: 'kpi',
            target_cell: 'C1502',
          },
        ],
        columns: [
          {
            name: 'Ventas',
            python_dtype: 'float64',
            power_bi_m_type: 'type number',
            semantic_role: 'numeric',
            excel_column_letter: 'C',
          },
        ],
        row_count: 1500,
      },
    };

    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(reportWithGuide);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-guide-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    const integrationTab = screen.getByRole('tab', { name: /Integración Power BI \/ Excel/i });
    fireEvent.click(integrationTab);

    expect(screen.getByText(/Generación Adaptativa v1.9.0/i)).toBeInTheDocument();
    expect(screen.getByText(/Total Registros:/i)).toBeInTheDocument();
    expect(screen.getByText('[Total_Ventas]')).toBeInTheDocument();
    expect(screen.getByText(/KPIs Directivos/i)).toBeInTheDocument();
    expect(screen.getByText(/Suma total de la métrica 'Ventas'/i)).toBeInTheDocument();
    expect(screen.getByText(/Mapeo de Columnas \(Excel \/ Power BI\)/i)).toBeInTheDocument();
    expect(screen.getByText('Col C')).toBeInTheDocument();

    // Enlaces de exportación directa
    const pbipLink = screen.getByRole('link', { name: /Proyecto PBIP/i });
    expect(pbipLink).toHaveAttribute('href', expect.stringContaining('/api/v1/analytics/run-guide-123/export/pbip'));

    const tmdlLink = screen.getByRole('link', { name: /Modelo TMDL/i });
    expect(tmdlLink).toHaveAttribute('href', expect.stringContaining('/api/v1/analytics/run-guide-123/export/tmdl'));

    const daxLink = screen.getByRole('link', { name: /Medidas DAX/i });
    expect(daxLink).toHaveAttribute('href', expect.stringContaining('/api/v1/analytics/run-guide-123/export/dax'));

    // Cambiar a vista de Modelo TMDL
    const tmdlTabBtn = screen.getByRole('button', { name: /Modelo Semántico TMDL|Modelo TMDL/i });
    fireEvent.click(tmdlTabBtn);
    expect(screen.getByText(/table Ventas_Comerciales/i)).toBeInTheDocument();

    // Filtrar fórmulas Excel por categoría
    const kpiCategoryBtn = screen.getByRole('button', { name: /KPIs & Estadísticas|KPIs/i });
    fireEvent.click(kpiCategoryBtn);
    expect(screen.getAllByText(/Total Suma — Ventas/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders interactive Star Schema preview with dimensions, relationships and DAX when available', async () => {
    const reportWithStarSchema: ExecutiveAnalyticsReport = {
      ...mockReport,
      integration_guide: {
        table_name: 'Ventas_Comerciales',
        clean_filename: 'Ventas_Comerciales.csv',
        row_count: 1500,
        columns: [
          { name: 'Fecha', python_dtype: 'datetime64[ns]', power_bi_m_type: 'type datetime', semantic_role: 'date' },
          { name: 'Segmento', python_dtype: 'object', power_bi_m_type: 'type text', semantic_role: 'category' },
          { name: 'Ventas', python_dtype: 'float64', power_bi_m_type: 'type number', semantic_role: 'numeric' },
        ],
        power_query_m_csv: 'let\n    Source = Csv.Document(...)\nin\n    #"Changed Type"',
        dax_measures: [],
        excel_formulas: [],
        star_schema: {
          fact_table: 'Ventas_Comerciales',
          fact_rows: 1500,
          measures: ['Ventas'],
          dimension_count: 3,
          dimensions: [
            {
              name: 'Dim_Fecha',
              kind: 'calendar',
              source_column: 'Fecha',
              key_column: 'Date',
              distinct_count: 0,
              suggested_attributes: ['Año', 'Mes', 'Trimestre'],
              dax_definition: "Dim_Fecha = \nADDCOLUMNS(\n    CALENDAR(MIN('Ventas_Comerciales'[Fecha]), MAX('Ventas_Comerciales'[Fecha])),\n    \"Año\", YEAR([Date])\n)",
            },
            {
              name: 'Dim_Segmento',
              kind: 'attribute',
              source_column: 'Segmento',
              key_column: 'Segmento',
              distinct_count: 5,
              suggested_attributes: ['Segmento'],
              dax_definition: "Dim_Segmento = DISTINCT('Ventas_Comerciales'[Segmento])",
            },
            {
              name: 'Dim_Tienda',
              kind: 'attribute',
              source_column: 'Tienda',
              key_column: 'Tienda',
              distinct_count: 12,
              suggested_attributes: ['Tienda'],
              dax_definition: "Dim_Tienda = DISTINCT('Ventas_Comerciales'[Tienda])",
            },
          ],
          relationships: [
            { from_table: 'Ventas_Comerciales', from_column: 'Fecha', to_table: 'Dim_Fecha', to_column: 'Date', cardinality: 'many-to-one', cross_filter: 'single', is_active: true },
            { from_table: 'Ventas_Comerciales', from_column: 'Segmento', to_table: 'Dim_Segmento', to_column: 'Segmento', cardinality: 'many-to-one', cross_filter: 'single', is_active: true },
          ],
          dax_calculated_tables: "Dim_Fecha = \nADDCOLUMNS(\n    CALENDAR(...)\n)\n\nDim_Segmento = DISTINCT('Ventas_Comerciales'[Segmento])",
          tmdl_relationships: 'relationship Ventas_Comerciales_Fecha_Dim_Fecha\n\tfromColumn: Ventas_Comerciales.Fecha\n\ttoColumn: Dim_Fecha.Date',
        },
      },
    };

    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(reportWithStarSchema);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-star-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    const integrationTab = screen.getByRole('tab', { name: /Integración Power BI \/ Excel/i });
    fireEvent.click(integrationTab);

    // El botón de la vista Esquema Estrella aparece con el número de dimensiones
    const starBtn = screen.getByTestId('star-schema-view-btn');
    expect(starBtn).toHaveTextContent(/Esquema Estrella \(3\)/i);
    fireEvent.click(starBtn);

    // El diagrama muestra la tabla de hechos, las 3 dimensiones y su DAX consolidado
    expect(screen.getByTestId('star-schema-visual')).toBeInTheDocument();
    expect(screen.getByText(/Esquema Estrella — Ventas_Comerciales/i)).toBeInTheDocument();
    expect(screen.getByTestId('star-dim-Dim_Fecha')).toBeInTheDocument();
    expect(screen.getByTestId('star-dim-Dim_Segmento')).toBeInTheDocument();
    expect(screen.getByTestId('star-dim-Dim_Tienda')).toBeInTheDocument();
    expect(screen.getByText(/Dim_Segmento = DISTINCT\('Ventas_Comerciales'\[Segmento\]\)/i)).toBeInTheDocument();

    // Al hacer clic en una dimensión se inspecciona su clave y su DAX de creación
    fireEvent.click(screen.getByTestId('star-dim-Dim_Segmento'));
    expect(screen.getAllByText(/Dim_Segmento/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Atributos Sugeridos:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/DISTINCT\('Ventas_Comerciales'\[Segmento\]\)/i).length).toBeGreaterThanOrEqual(2);

    // Botón de exportación del diagrama a imagen PNG
    const pngBtn = screen.getByTestId('export-star-schema-png-btn');
    expect(pngBtn).toBeInTheDocument();
    expect(pngBtn).toHaveTextContent(/Exportar PNG|Descargar PNG/i);
    fireEvent.click(pngBtn);
  });

  it('does not show the Star Schema view button when the guide has no star schema', async () => {
    const reportWithGuide: ExecutiveAnalyticsReport = {
      ...mockReport,
      integration_guide: {
        table_name: 'Ventas_Comerciales',
        clean_filename: 'Ventas_Comerciales.csv',
        row_count: 1500,
        columns: [],
        power_query_m_csv: 'let\n    Source = Csv.Document(...)\nin\n    #"Changed Type"',
        dax_measures: [],
        excel_formulas: [],
      },
    };

    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(reportWithGuide);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-no-star" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /Integración Power BI \/ Excel/i }));
    expect(screen.queryByTestId('star-schema-view-btn')).not.toBeInTheDocument();
  });

  it('does not crash and renders defaults when report.integration_guide is undefined', async () => {
    const reportWithoutGuide: ExecutiveAnalyticsReport = {
      ...mockReport,
      integration_guide: undefined,
    };

    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(reportWithoutGuide);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-no-guide" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    const integrationTab = screen.getByRole('tab', { name: /Integración Power BI \/ Excel/i });
    fireEvent.click(integrationTab);

    expect(screen.getByText(/Guía de Integración y Fórmulas para Power BI y Excel/i)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft Power BI/i)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft Excel/i)).toBeInTheDocument();
    expect(screen.getByText(/Total_Registros = COUNTROWS/i)).toBeInTheDocument();
  });

  it('allows switching to drift tab, displays drift status, proactive recommendations and percentiles', async () => {
    vi.spyOn(api, 'getBusinessAnalytics').mockResolvedValue(mockReport);

    render(
      <LanguageProvider>
        <BusinessInsights runId="run-test-123" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Facturación Total Estimada')).toBeInTheDocument();
    });

    const driftTab = screen.getByRole('tab', { name: /Alertas & Data Drift/i });
    fireEvent.click(driftTab);

    expect(screen.getByText(/Distribución Estadística Estable/i)).toBeInTheDocument();
    expect(screen.getByText(/Acotar valores atípicos en Precio_Unidad/i)).toBeInTheDocument();
    expect(screen.getByText(/Desplazamiento de Percentiles \(P05 a P95\)/i)).toBeInTheDocument();
    expect(screen.getByText(/P50 \(Mediana Central\)/i)).toBeInTheDocument();
    expect(screen.getAllByText('4.2%').length).toBeGreaterThanOrEqual(1);
  });
});
