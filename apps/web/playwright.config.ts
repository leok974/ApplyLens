import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const CI = !!process.env.CI
const PORT = process.env.PORT ? Number(process.env.PORT) : 5173
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`
const STORAGE_STATE = process.env.STORAGE_STATE || 'tests/.auth/state.json'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  testDir: 'tests/e2e',
  /* Speedy local dev; resilient CI */
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 2 : 0,
  workers: process.env.PW_WORKERS
    ? (isNaN(Number(process.env.PW_WORKERS)) ? (process.env.PW_WORKERS as any) : Number(process.env.PW_WORKERS))
    : CI
      ? '100%'
      : '50%',
  reporter: CI
    ? [
        ['list'],
        ['junit', { outputFile: 'reports/junit.xml' }],
        ['html', { outputFolder: 'reports/html', open: 'never' }],
      ]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    video: CI ? 'retain-on-failure' : 'on-first-retry',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    viewport: { width: 1280, height: 800 },
    // Strict mode helps catch sloppy selectors
    launchOptions: {
      args: ['--disable-dev-shm-usage'],
    },
  },
  /* Projects: fast + representative */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Auth-enabled project (uses persistent storageState)
    {
      name: 'chromium-auth',
      use: {
        ...devices['Desktop Chrome'],
        storageState: STORAGE_STATE,
      },
    },
    {
      name: 'chromium-no-animations',
      use: {
        ...devices['Desktop Chrome'],
        colorScheme: 'dark',
      },
    },
    // Uncomment if you want extra cross-browser coverage
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  /* Reuse an existing dev server locally; build+preview in CI for parity */
  webServer: CI
    ? [
        // Vite preview of the built app -> closest to production
        {
          command: `npm run build && npm run preview -- --port ${PORT}`,
          cwd: __dirname,
          port: PORT,
          reuseExistingServer: false,
          timeout: 120_000,
        },
      ]
    : [
        {
          command: 'npm run dev',
          cwd: __dirname,
          port: PORT, // can be overridden by env PORT
          reuseExistingServer: true,
          timeout: 120_000,
        },
      ],
})
