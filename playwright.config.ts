import { defineConfig, devices } from "@playwright/test";

const python = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : "python";
const backendPort = process.env.E2E_BACKEND_PORT ?? "8000";
const frontendPort = process.env.E2E_FRONTEND_PORT ?? "5173";
const backendURL = process.env.E2E_API_BASE ?? `http://localhost:${backendPort}`;
const frontendURL = `http://localhost:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: frontendURL,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} -m uvicorn backend.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `${backendURL}/health`,
      env: { CORS_ORIGINS: frontendURL },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: frontendURL,
      env: { VITE_API_BASE: backendURL },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
