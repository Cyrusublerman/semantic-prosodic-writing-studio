import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120000,
  use: {
    headless: true,
    baseURL: process.env.SPWS_WEB_URL || "http://127.0.0.1:4173",
  },
  webServer: process.env.SPWS_SKIP_WEBSERVER
    ? undefined
    : {
        command: "pnpm preview --host 127.0.0.1 --port 4173",
        port: 4173,
        reuseExistingServer: true,
      },
});
