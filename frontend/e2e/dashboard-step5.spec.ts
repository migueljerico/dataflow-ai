import { test, expect, Page } from '@playwright/test';
import { fileURLToPath } from 'url';
import { readFileSync } from 'fs';

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

test.describe('Paso 5 — Edición HITL, historial, exports, guía Power BI e i18n (E2E)', () => {
  test('alcanza el Paso 5 y cubre edición HITL, carga desde historial, descargas PNG/PDF/HTML, TMDL/PBIP, la guía y el cambio de idioma', async ({ page }) => {
    // El flujo completo (perfilado → plan → ejecución → esquema estrella → Blueprint) es largo.
    test.setTimeout(600_000);

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

    // ── Edición HITL: el usuario edita y Python revalida al guardar ──────────
    const originalName = (await page.locator('[data-testid="blueprint-title"]').textContent()) ?? '';
    const editedName = `${originalName} — editado HITL`;
    await page.locator('[data-testid="edit-blueprint-btn"]').click();
    const editor = page.locator('[data-testid="dashboard-editor"]');
    await expect(editor).toBeVisible();
    await expect(editor.locator('[data-testid="edit-name-input"]')).toHaveValue(originalName);
    await editor.locator('[data-testid="edit-name-input"]').fill(editedName);
    // Guardar y revalidar vive en el footer del Preview (junto al panel del editor).
    await page.locator('[data-testid="edit-save-btn"]').click();
    await expect(editor).toBeHidden({ timeout: 60_000 });
    await expect(page.locator('[data-testid="blueprint-title"]')).toHaveText(editedName);
    // La revalidación determinista vuelve a exponer el badge de checks.
    await expect(page.locator('[data-testid="validation-badge"]')).toBeVisible();

    // ── Historial: persistencia real en backend + carga (history-load-*) ─────
    await page.locator('[data-testid="history-btn"]').click();
    await expect(historyPanel).toBeVisible();

    const listRes = await page.request.get('/api/v1/dashboard');
    expect(listRes.status()).toBe(200);
    const listJson = await listRes.json();
    expect(listJson.items.length).toBeGreaterThan(0);
    expect(listJson.items.some((item: { name: string }) => item.name === editedName)).toBe(true);
    expect(listJson.retention_days).toBe(30);

    const currentItem = historyPanel.locator('[data-testid^="history-item-"]').first();
    await expect(currentItem).toContainText(editedName);
    await expect(historyPanel.locator('[data-testid="history-current-mark"]')).toBeVisible();

    const loadBtn = page.locator('[data-testid^="history-load-"]').first();
    await expect(loadBtn).toBeEnabled();
    await loadBtn.click();
    await expect(historyPanel).toBeHidden({ timeout: 30_000 });
    await expect(page.locator('[data-testid="dashboard-preview"]')).toBeVisible();
    await expect(page.locator('[data-testid="blueprint-title"]')).toHaveText(editedName);

    // ── Guía paso a paso: construcción del Dashboard en Power BI (ES) ─────────
    await page.locator('button', { hasText: /^Guía paso a paso$/ }).click();
    const guide = page.locator('[data-testid="powerbi-guide"]');
    await expect(guide).toBeVisible();
    for (let step = 1; step <= 5; step += 1) {
      await expect(guide.locator(`[data-testid="powerbi-guide-step-${step}"]`)).toBeVisible();
    }
    // Rutas reales de la interfaz (verificadas contra Microsoft Learn)
    await expect(guide.locator('[data-testid="powerbi-guide-step-2-route"]')).toContainText('Modeling → New measure');
    await expect(guide.locator('[data-testid="powerbi-guide-step-3-route"]')).toContainText('Insertar → Elementos → Formas');
    await expect(guide.locator('[data-testid="powerbi-guide-step-4"]')).toContainText('esquinas redondeadas');
    await expect(guide.locator('[data-testid="powerbi-guide-step-5"]')).toContainText('Eje de tendencia');
    // Fuentes oficiales localizadas (es-es)
    const sourceHref = await guide.locator('[data-testid="powerbi-guide-sources"] a').first().getAttribute('href');
    expect(sourceHref).toContain('/es-es/power-bi/transform-model/desktop-measures');

    // ── Descargas de la maqueta ejecutiva: PNG, PDF y HTML ───────────────────
    await page.locator('button', { hasText: /^Ejemplo$/ }).click();
    await expect(mockup).toBeVisible();

    const pngDownloadPromise = page.waitForEvent('download');
    await page.locator('[data-testid="export-dashboard-mockup-png-btn"]').click();
    const pngDownload = await pngDownloadPromise;
    expect(pngDownload.suggestedFilename()).toMatch(/^dashboard_dbp_[A-Za-z0-9_-]+\.png$/);
    const pngPath = await pngDownload.path();
    expect(pngPath).toBeTruthy();
    const pngBytes = readFileSync(pngPath!);
    // Magic number PNG: 89 50 4E 47 0D 0A 1A 0A
    expect(Array.from(pngBytes.subarray(0, 8))).toEqual([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    expect(pngBytes.length).toBeGreaterThan(10_000);

    const pdfDownloadPromise = page.waitForEvent('download');
    await page.locator('[data-testid="export-dashboard-mockup-pdf-btn"]').click();
    const pdfDownload = await pdfDownloadPromise;
    expect(pdfDownload.suggestedFilename()).toMatch(/^dashboard_dbp_[A-Za-z0-9_-]+\.pdf$/);
    const pdfPath = await pdfDownload.path();
    expect(pdfPath).toBeTruthy();
    const pdfHead = readFileSync(pdfPath!).subarray(0, 5).toString('latin1');
    expect(pdfHead).toBe('%PDF-');

    const htmlDownloadPromise = page.waitForEvent('download');
    await page.locator('[data-testid="export-dashboard-mockup-html-btn"]').click();
    const htmlDownload = await htmlDownloadPromise;
    expect(htmlDownload.suggestedFilename()).toMatch(/^dashboard_dbp_[A-Za-z0-9_-]+\.html$/);
    const htmlPath = await htmlDownload.path();
    expect(htmlPath).toBeTruthy();
    const htmlText = readFileSync(htmlPath!, 'utf-8');
    expect(htmlText).toContain('<!DOCTYPE html>');
    expect(htmlText).toContain('<svg');
    expect(htmlText).toContain('DataFlow AI');

    // ── Cambio de idioma sobre la maqueta (ES → EN → ES) ──────────────────────
    await switchLanguage(page, /english/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(mockup.locator('h3').first()).toHaveText('Dashboard visual example');

    // La guía también se traduce al inglés (i18n es/en completo)
    await page.locator('button', { hasText: /^Step-by-step guide$/ }).click();
    await expect(guide).toBeVisible();
    await expect(guide.locator('[data-testid="powerbi-guide-title"]')).toContainText('build your Dashboard in Power BI');
    await expect(guide.locator('[data-testid="powerbi-guide-step-4"]')).toContainText('Rounded corners');
    const sourceHrefEn = await guide.locator('[data-testid="powerbi-guide-sources"] a').first().getAttribute('href');
    expect(sourceHrefEn).toContain('/en-us/power-bi/transform-model/desktop-measures');

    await page.locator('[data-testid="history-btn"]').click();
    await expect(historyPanel.getByText(/Retention:\s*30\s*days/)).toBeVisible({ timeout: 30_000 });
    await page.locator('[data-testid="history-close-btn"]').click();

    await switchLanguage(page, /español/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'es');
    await page.locator('button', { hasText: /^Ejemplo$/ }).click();
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
