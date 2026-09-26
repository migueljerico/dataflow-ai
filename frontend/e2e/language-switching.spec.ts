import { test, expect } from '@playwright/test';

test.describe('Language Switching & Bidirectional Layout E2E', () => {
  test('allows switching between languages and adapts document direction (LTR/RTL)', async ({ page }) => {
    await page.goto('/');

    // 1. Verificar estado inicial en español
    await expect(page.locator('h1')).toContainText('DataFlow AI');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');

    // 2. Cambiar a Inglés (EN)
    await page.locator('button[aria-haspopup="listbox"]').click();
    await page.getByRole('option', { name: /english/i }).click();

    // Comprobar textos en inglés
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toContainText('EN');

    // 3. Cambiar a Alemán (DE)
    await page.locator('button[aria-haspopup="listbox"]').click();
    await page.getByRole('option', { name: /deutsch/i }).click();

    await expect(page.locator('html')).toHaveAttribute('lang', 'de');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toContainText('DE');

    // 4. Cambiar a Francés (FR)
    await page.locator('button[aria-haspopup="listbox"]').click();
    await page.getByRole('option', { name: /français/i }).click();

    await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toContainText('FR');

    // 5. Cambiar a Árabe (AR) y verificar soporte bidireccional RTL
    await page.locator('button[aria-haspopup="listbox"]').click();
    await page.getByRole('option', { name: /العربية/i }).click();

    await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toContainText('AR');

    // 6. Volver a Español (ES) y comprobar retorno a LTR
    await page.locator('button[aria-haspopup="listbox"]').click();
    await page.getByRole('option', { name: /español/i }).click();

    await expect(page.locator('html')).toHaveAttribute('lang', 'es');
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
    await expect(page.locator('button[aria-haspopup="listbox"]')).toContainText('ES');
  });
});
