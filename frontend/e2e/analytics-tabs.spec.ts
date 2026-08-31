import { test, expect } from '@playwright/test';

test.describe('Business Analytics Tabs & Interactive Visualizations E2E', () => {
  test('navigates through KPIs, Clusters 2D, Outliers Boxplot and Power BI / Excel integration', async ({ page }) => {
    await page.goto('/');

    // 1. Cargar demo y ejecutar plan
    const sampleCard = page.locator('text=Contact Center & Operaciones').first();
    await expect(sampleCard).toBeVisible({ timeout: 10000 });
    await sampleCard.click();

    const proposeRulesBtn = page.getByRole('button', { name: /reglas deterministas/i });
    await expect(proposeRulesBtn).toBeVisible({ timeout: 20000 });
    await proposeRulesBtn.click();

    const executeBtn = page.getByRole('button', { name: /ejecutar plan/i });
    await expect(executeBtn).toBeVisible({ timeout: 20000 });
    await executeBtn.click();

    // 2. Esperar carga de Business Analytics
    await expect(page.getByRole('heading', { name: /transformación completada con éxito/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Business Analytics & KPIs Ejecutivos')).toBeVisible({ timeout: 20000 });

    // 3. Tab 1: KPIs y Resumen Directivo
    await expect(page.getByText('Resumen Ejecutivo para Dirección')).toBeVisible();
    await expect(page.getByText('Recomendaciones de Negocio')).toBeVisible();

    // 4. Tab 2: Clusters 2D Scatter
    const tabClusters = page.getByRole('tab', { name: /segmentación de clusters/i });
    await expect(tabClusters).toBeVisible();
    await tabClusters.click();

    // Verificar renderizado de SVG y selectores de ejes
    await expect(page.locator('svg').first()).toBeVisible();
    await expect(page.getByText(/eje x \(horizontal\)/i)).toBeVisible();
    await expect(page.getByText(/eje y \(vertical\)/i)).toBeVisible();

    // 5. Tab 3: Outliers Boxplots y Dispersión
    const tabOutliers = page.getByRole('tab', { name: /detección de outliers/i });
    await expect(tabOutliers).toBeVisible();
    await tabOutliers.click();

    // Verificar diagrama Boxplot
    await expect(page.getByText(/valores atípicos/i)).toBeVisible();
    await expect(page.getByText(/q1 \(25%\)/i)).toBeVisible();
    await expect(page.getByText(/mediana \(q2\)/i)).toBeVisible();
    await expect(page.getByText(/q3 \(75%\)/i)).toBeVisible();

    // Conmutar a vista de dispersión (Scatter)
    const scatterViewBtn = page.getByRole('button', { name: /dispersión/i });
    await expect(scatterViewBtn).toBeVisible();
    await scatterViewBtn.click();
    await expect(page.getByText(/max iqr/i)).toBeVisible();

    // 6. Tab 4: Integración Power BI y Excel
    const tabIntegration = page.getByRole('tab', { name: /integración power bi \/ excel/i });
    await expect(tabIntegration).toBeVisible();
    await tabIntegration.click();

    // Verificar secciones de Power BI (DAX, M) y Excel
    await expect(page.getByText(/microsoft power bi/i)).toBeVisible();
    await expect(page.getByText(/medida dax sugerida/i)).toBeVisible();
    await expect(page.getByText(/power query m/i)).toBeVisible();
    await expect(page.getByText(/microsoft excel/i)).toBeVisible();
    await expect(page.getByText(/fórmula de validación excel/i)).toBeVisible();
  });
});
