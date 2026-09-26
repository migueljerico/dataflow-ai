import { test, expect, Page } from '@playwright/test';
import { fileURLToPath } from 'url';

// Lote de dos datasets demo para alcanzar el flujo multi-archivo (Paso 5).
const SAMPLE_PATHS = [
  fileURLToPath(new URL('../../data_samples/sales_sample_corrupted.csv', import.meta.url)),
  fileURLToPath(new URL('../../data_samples/contact_center_corrupted.csv', import.meta.url)),
];

/** Abre el selector de idioma global y elige una opción del listado. */
const switchLanguage = async (page: Page, option: RegExp) => {
  // El aria-label del disparador se traduce con el idioma activo, por eso se
  // localiza por su semántica de listbox (única en la aplicación).
  await page.locator('button[aria-haspopup="listbox"]').click();
  await page.getByRole('option', { name: option }).click();
};

test.describe('Paso 5 — Historial, export TMDL/PBIP e i18n de la maqueta (E2E)', () => {
  test('alcanza el Paso 5 desde un lote, valida el historial con retención, descarga TMDL/PBIP y cambia de idioma en la maqueta', async ({ page }) => {
    // El flujo completo (perfilado → plan → ejecución → esquema estrella → Blueprint) es largo.
    test.setTimeout(300_000);

    // ── Paso 1: carga de un lote de dos datasets demo ────────────────────────
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('DataFlow AI');
    await page.locator('#fileInput').setInputFiles(SAMPLE_PATHS);

    // ── Paso 2: perfilado del lote y plan por reglas deterministas ────────────
    const rulesBtn = page.getByRole('button', { name: /reglas deterministas \(todas\)/i });
    await expect(rulesBtn).toBeVisible({ timeout: 60_000 });
    await rulesBtn.click();

    // ── Paso 3: aprobación humana y ejecución de la limpieza del lote ────────
    const cleanAllBtn = page.getByRole('button', { name: /aprobar y limpiar todas \(\d+ pasos?\)/i });
    await expect(cleanAllBtn).toBeVisible({ timeout: 60_000 });
    await cleanAllBtn.click();

    // ── Paso 4: esquema estrella (auto-generado) → entrada al Paso 5 ─────────
    // El Blueprint puede estar pre-generado tras el lote ("Ver Dashboard
    // Preview") o haberse de generar a demanda ("Generar Propuesta de Dashboard").
    const enterStep5 = page.locator('[data-testid="go-dashboard-preview"], [data-testid="generate-dashboard"]').first();
    await expect(enterStep5).toBeVisible({ timeout: 60_000 });
    await expect(enterStep5).toBeEnabled({ timeout: 90_000 });

    // ── Paso 5: generación del Blueprint y entrada al Preview ─────────────────
    await enterStep5.click();
    await expect(page.locator('[data-testid="dashboard-preview"]')).toBeVisible({ timeout: 90_000 });

    // La maqueta del Paso 5 es la pestaña por defecto y arranca en español.
    const mockup = page.locator('[data-testid="dashboard-mockup"]');
    await expect(mockup).toBeVisible();
    await expect(mockup.locator('h3').first()).toHaveText('Ejemplo visual del dashboard');

    // ── Historial de propuestas con retención (TTL) ───────────────────────────
    await page.locator('[data-testid="history-btn"]').click();
    const historyPanel = page.locator('[data-testid="history-panel"]');
    await expect(historyPanel).toBeVisible();
    await expect(historyPanel.getByText(/Retención:\s*30\s*días/)).toBeVisible({ timeout: 30_000 });

    // El Blueprint recién generado debe figurar en el historial y marcarse como actual.
    const historyItems = historyPanel.locator('[data-testid^="history-item-"]');
    await expect(historyItems.first()).toBeVisible();
    expect(await historyItems.count()).toBeGreaterThan(0);
    await expect(historyPanel.locator('[data-testid="history-current-mark"]')).toBeVisible();

    await page.locator('[data-testid="history-close-btn"]').click();
    await expect(historyPanel).toBeHidden();

    // ── Cambio de idioma sobre la maqueta (ES → EN → ES) ──────────────────────
    await switchLanguage(page, /english/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(mockup.locator('h3').first()).toHaveText('Dashboard visual example');

    await page.locator('[data-testid="history-btn"]').click();
    await expect(historyPanel.getByText(/Retention:\s*30\s*days/)).toBeVisible({ timeout: 30_000 });
    await page.locator('[data-testid="history-close-btn"]').click();

    await switchLanguage(page, /español/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'es');
    await expect(mockup.locator('h3').first()).toHaveText('Ejemplo visual del dashboard');

    // ── Export del modelo editado: TMDL y proyecto .pbip ──────────────────────
    await page.locator('button', { hasText: /^Power BI$/ }).click();
    await expect(page.locator('[data-testid="export-model-card"]')).toBeVisible();

    const tmdlUrl = await page.locator('[data-testid="export-tmdl-btn"]').getAttribute('href');
    expect(tmdlUrl).toMatch(/\/api\/v1\/dashboard\/dbp_[a-f0-9]+\/export\/tmdl$/);

    const tmdlRes = await page.request.get(tmdlUrl!);
    expect(tmdlRes.status()).toBe(200);
    expect(tmdlRes.headers()['content-type']).toContain('text/plain');
    expect(tmdlRes.headers()['content-disposition']).toContain('.tmdl"');
    const tmdlText = await tmdlRes.text();
    expect(tmdlText).toMatch(/^model Model/);
    expect(tmdlText).toContain("measure '");
    expect(tmdlText.length).toBeGreaterThan(500);

    const pbipUrl = await page.locator('[data-testid="export-pbip-btn"]').getAttribute('href');
    expect(pbipUrl).toMatch(/\/api\/v1\/dashboard\/dbp_[a-f0-9]+\/export\/pbip$/);

    const pbipRes = await page.request.get(pbipUrl!);
    expect(pbipRes.status()).toBe(200);
    expect(pbipRes.headers()['content-type']).toContain('application/zip');
    expect(pbipRes.headers()['content-disposition']).toContain('.pbip.zip"');
    const pbipBuffer = await pbipRes.body();
    expect(pbipBuffer.subarray(0, 2).toString()).toBe('PK');
    expect(pbipBuffer.length).toBeGreaterThan(500);
  });
});
