import { defineConfig, devices } from '@playwright/test';

const isWindows = process.platform === 'win32';

/**
 * Intérprete de Python del backend (Paso 5 / API).
 * - Windows (desarrollo local): la venv del repositorio (backend/venv).
 * - Linux/macOS y CI: la venv equivalente, salvo que DF_PYTHON lo sobrescriba
 *   (en GitHub Actions se usa el Python del runner: DF_PYTHON=python3).
 */
const backendPython =
  process.env.DF_PYTHON ?? (isWindows ? 'venv\\Scripts\\python.exe' : 'venv/bin/python');

/** npm cross-platform: en Windows el binario es npm.cmd. */
const npm = isWindows ? 'npm.cmd' : 'npm';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `${backendPython} -m uvicorn app.main:app --port 8000`,
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/api/v1/datasets/samples',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: `${npm} run dev -- --port 3000`,
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
