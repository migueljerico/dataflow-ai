import { test, expect } from '@playwright/test';

test.describe('End-to-End Dataset Processing & Multi-Format Export Flows', () => {
  test('executes end-to-end pipeline and exports clean CSV, native Parquet, Python script and HTML report', async ({ page }) => {
    // 1. Ir a la app
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('DataFlow AI');

    // 2. Cargar dataset demo 'Contact Center & Operaciones'
    const sampleCard = page.locator('text=Contact Center & Operaciones').first();
    await expect(sampleCard).toBeVisible({ timeout: 10000 });
    await sampleCard.click();

    // 3. Paso 2: Perfilado y Calidad
    await expect(page.locator('.score-banner')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('.score-num')).toBeVisible();

    // Proponer plan con reglas deterministas
    const proposeRulesBtn = page.getByRole('button', { name: /reglas deterministas/i });
    await expect(proposeRulesBtn).toBeVisible({ timeout: 10000 });
    await proposeRulesBtn.click();

    // 4. Paso 3: Revisión del Plan Human-in-the-Loop
    const executeBtn = page.getByRole('button', { name: /ejecutar plan/i });
    await expect(executeBtn).toBeVisible({ timeout: 20000 });
    await executeBtn.click();

    // 5. Paso 4: Informe de Ejecución y Reporte
    await expect(page.getByRole('heading', { name: /transformación completada con éxito/i })).toBeVisible({ timeout: 20000 });

    // Validar visualización de estadísticas
    await expect(page.getByText(/run id:/i)).toBeVisible();
    await expect(page.getByText(/quality score estimado/i)).toBeVisible();

    // 6. Verificar enlaces de descarga de los 4 artefactos
    const downloadCsvLink = page.getByRole('link', { name: /descargar dataset limpio/i });
    await expect(downloadCsvLink).toBeVisible();
    const csvHref = await downloadCsvLink.getAttribute('href');
    expect(csvHref).toMatch(/\/api\/v1\/runs\/RUN-[a-f0-9]+\/download/);

    const downloadParquetLink = page.getByRole('link', { name: /descargar parquet \(arrow\)/i });
    await expect(downloadParquetLink).toBeVisible();
    const parquetHref = await downloadParquetLink.getAttribute('href');
    expect(parquetHref).toMatch(/\/api\/v1\/runs\/RUN-[a-f0-9]+\/download-parquet/);

    const downloadScriptLink = page.getByRole('link', { name: /descargar script python/i });
    await expect(downloadScriptLink).toBeVisible();
    const scriptHref = await downloadScriptLink.getAttribute('href');
    expect(scriptHref).toMatch(/\/api\/v1\/runs\/RUN-[a-f0-9]+\/download-script/);

    // 7. Descargar y validar integridad binaria directa de los endpoints
    const resCsv = await page.request.get(csvHref!);
    expect(resCsv.status()).toBe(200);
    const csvText = await resCsv.text();
    expect(csvText.length).toBeGreaterThan(50);
    expect(csvText).toContain(',');

    const resParquet = await page.request.get(parquetHref!);
    expect(resParquet.status()).toBe(200);
    const parquetBuffer = await resParquet.body();
    expect(parquetBuffer.length).toBeGreaterThan(100);
    // Magic number de Apache Parquet: PAR1 al inicio y al final
    expect(parquetBuffer.subarray(0, 4).toString()).toBe('PAR1');
    expect(parquetBuffer.subarray(parquetBuffer.length - 4).toString()).toBe('PAR1');

    const resScript = await page.request.get(scriptHref!);
    expect(resScript.status()).toBe(200);
    const scriptText = await resScript.text();
    expect(scriptText).toContain('DataFlow AI — Reproducible ETL Pipeline Script');
    expect(scriptText).toContain('def run_etl_pipeline');

    // 8. Validar exportación del informe ejecutivo en HTML
    const exportHtmlLink = page.getByRole('link', { name: /exportar reporte ejecutivo/i });
    await expect(exportHtmlLink).toBeVisible();
    const htmlHref = await exportHtmlLink.getAttribute('href');
    expect(htmlHref).toContain('/api/v1/analytics/RUN-');
    expect(htmlHref).toContain('/export');

    const resHtml = await page.request.get(htmlHref!);
    expect(resHtml.status()).toBe(200);
    const htmlText = await resHtml.text();
    expect(htmlText).toContain('<!DOCTYPE html>');
    expect(htmlText).toContain('DataFlow AI — Reporte Ejecutivo de Business Analytics');
    expect(htmlText).toContain('<svg');

    // 9. Resetear sesión y regresar al Paso 1
    const resetBtn = page.getByRole('button', { name: /limpiar otro dataset/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    await expect(page.getByRole('heading', { name: /cargar dataset empresarial/i })).toBeVisible({ timeout: 10000 });
  });
});
