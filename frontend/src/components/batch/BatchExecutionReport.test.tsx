import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BatchExecutionReport, BatchExecutionItem } from './BatchExecutionReport';
import { LanguageProvider } from '../../context/LanguageContext';

// Mock de subcomponentes para aislar la prueba unitaria
vi.mock('../BusinessInsights', () => ({
  BusinessInsights: ({ runId }: { runId: string }) => (
    <div data-testid="mock-business-insights">BusinessInsights for {runId}</div>
  ),
}));

vi.mock('../MultiTableStarSchema', () => ({
  MultiTableStarSchemaViewer: () => (
    <div data-testid="mock-star-schema-viewer">Mock Star Schema Viewer</div>
  ),
}));

const mockResults: BatchExecutionItem[] = [
  {
    datasetId: 'ds_1',
    filename: 'order_details.csv',
    result: {
      run_id: 'run_order_details',
      dataset_id: 'ds_1',
      plan_id: 'plan_1',
      status: 'completed',
      started_at: '2026-09-05T10:00:00Z',
      finished_at: '2026-09-05T10:01:00Z',
      rows_before: 100,
      rows_after: 95,
      columns_before: 5,
      columns_after: 5,
      applied_steps_count: 3,
      input_hash_md5: 'hash_in_1',
      output_hash_md5: 'hash_out_1',
      clean_filename: 'clean_order_details.csv',
      download_url: '/api/v1/runs/run_order_details/download',
      script_url: '/api/v1/runs/run_order_details/script',
      parquet_filename: 'clean_order_details.parquet',
      parquet_url: '/api/v1/runs/run_order_details/parquet',
      errors: [],
      warnings: [],
    },
    scoreBefore: 85,
    scoreAfter: 97,
    scoreDelta: 12,
  },
  {
    datasetId: 'ds_2',
    filename: 'products.csv',
    result: {
      run_id: 'run_products',
      dataset_id: 'ds_2',
      plan_id: 'plan_2',
      status: 'completed',
      started_at: '2026-09-05T10:00:00Z',
      finished_at: '2026-09-05T10:01:00Z',
      rows_before: 50,
      rows_after: 50,
      columns_before: 4,
      columns_after: 4,
      applied_steps_count: 2,
      input_hash_md5: 'hash_in_2',
      output_hash_md5: 'hash_out_2',
      clean_filename: 'clean_products.csv',
      download_url: '/api/v1/runs/run_products/download',
      script_url: '/api/v1/runs/run_products/script',
      parquet_filename: 'clean_products.parquet',
      parquet_url: '/api/v1/runs/run_products/parquet',
      errors: [],
      warnings: [],
    },
    scoreBefore: 90,
    scoreAfter: 99,
    scoreDelta: 9,
  },
];

describe('BatchExecutionReport Component', () => {
  it('renderiza cabecera, botón ZIP masivo y descargas destacadas de todos los datasets', () => {
    const onReset = vi.fn();
    const onGenStar = vi.fn();

    render(
      <LanguageProvider>
        <BatchExecutionReport
          results={mockResults}
          cleanStarSchema={null}
          loadingStarSchema={false}
          onGenerateStarSchema={onGenStar}
          onResetSession={onReset}
        />
      </LanguageProvider>
    );

    // 1. Cabecera y botón ZIP
    expect(screen.getByText(/¡Lote de 2 Tablas Limpiado con Éxito!/i)).toBeInTheDocument();
    const zipBtn = screen.getByRole('link', { name: /Descargar Lote Completo \(\.ZIP\)/i });
    expect(zipBtn).toBeInTheDocument();
    expect(zipBtn).toHaveAttribute('href', expect.stringContaining('/runs/batch/download-zip'));

    // 2. Descargas de cada tabla
    expect(screen.getAllByText('order_details.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('products.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('clean_order_details.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('clean_products.csv').length).toBeGreaterThanOrEqual(1);

    const csvLinks = screen.getAllByRole('link', { name: /Descargar CSV/i });
    expect(csvLinks.length).toBe(2);

    const parquetLinks = screen.getAllByRole('link', { name: /Parquet/i });
    expect(parquetLinks.length).toBe(2);

    const scriptLinks = screen.getAllByRole('link', { name: /Script \.py/i });
    expect(scriptLinks.length).toBe(2);

    // 3. BusinessInsights se renderiza para la tabla activa (por defecto la primera o fact)
    const insights = screen.getByTestId('mock-business-insights');
    expect(insights).toBeInTheDocument();
    expect(insights).toHaveTextContent('BusinessInsights for run_order_details');

    // 4. Esquema de Estrella seccion final
    expect(screen.getByText(/7️⃣ Esquema de Estrella del Modelo Semántico Limpio/i)).toBeInTheDocument();
  });

  it('permite alternar entre tablas en el selector para ver sus insights y formulas DAX', () => {
    const onReset = vi.fn();
    const onGenStar = vi.fn();

    render(
      <LanguageProvider>
        <BatchExecutionReport
          results={mockResults}
          cleanStarSchema={null}
          loadingStarSchema={false}
          onGenerateStarSchema={onGenStar}
          onResetSession={onReset}
        />
      </LanguageProvider>
    );

    // Click en la pestaña de 'products.csv'
    const productsPill = screen.getByRole('button', { name: /products\.csv/i });
    fireEvent.click(productsPill);

    // Ahora BusinessInsights debe mostrarse para run_products
    expect(screen.getByTestId('mock-business-insights')).toHaveTextContent('BusinessInsights for run_products');
  });
});
