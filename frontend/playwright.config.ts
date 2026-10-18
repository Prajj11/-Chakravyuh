import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
const root = resolve(__dirname, "..");
const localPython =
  process.platform === "win32"
    ? resolve(root, ".venv/Scripts/python.exe")
    : resolve(root, ".venv/bin/python");
const python =
  process.env.PW_PYTHON ?? (existsSync(localPython) ? localPython : "python");
process.env.PW_PYTHON = python;
const runtime = resolve(root, ".runtime/e2e");
process.env.PW_TOKEN_FILE ??= resolve(runtime, "local-session-token");
export default defineConfig({
  testDir: "./e2e",
  timeout: 180000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  outputDir: "../.runtime/e2e-results",
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    actionTimeout: 15000,
    viewport: { width: 1600, height: 1000 },
    channel: process.platform === "win32" ? "msedge" : undefined,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --loop asyncio`,
      cwd: root,
      url: "http://127.0.0.1:8001/api/v1/health",
      reuseExistingServer: !process.env.CI,
      env: { CHAKRAVYUH_DATA_DIR: runtime },
    },
    {
      command: "npm run start",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
