import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
const database = process.env.TEST_DATABASE_URL;
if (
  !database ||
  !new URL(
    database.replace("postgresql+psycopg:", "postgresql:"),
  ).pathname.endsWith("_test")
)
  throw new Error(
    "Define TEST_DATABASE_URL con una base aislada terminada en _test.",
  );
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  expect: { timeout: 10000 },
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 370, height: 800 },
    deviceScaleFactor: 2,
    timezoneId: "America/Lima",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.CHROMIUM_PATH
      ? { executablePath: process.env.CHROMIUM_PATH }
      : {},
  },
  reporter: [["list"], ["html", { open: "never" }]],
  webServer: [
    {
      command: `"${process.env.PYTHON_BIN || fileURLToPath(new URL("../backend/.venv/Scripts/python.exe", import.meta.url))}" -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/api/health",
      timeout: 30000,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: database,
        AI_PROVIDER: "nvidia",
        GROQ_API_KEY: "",
        NVIDIA_API_KEY: "",
        NVIDIA_MODEL: "",
        CORS_ORIGINS: JSON.stringify([
          "http://127.0.0.1:5174",
          "http://127.0.0.1:5175",
        ]),
      },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      timeout: 30000,
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
    },
    {
      command: "npm run preview -- --port 5175",
      url: "http://127.0.0.1:5175",
      timeout: 30000,
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
    },
  ],
});
