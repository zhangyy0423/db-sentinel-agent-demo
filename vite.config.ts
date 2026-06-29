import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { configValue, intConfigValue, readAppConfig } from "./scripts/config.mjs";

const appConfig = readAppConfig();
const backendHost = configValue(appConfig, "backend", "host", "127.0.0.1", ["BACKEND_HOST"]);
const backendPort = intConfigValue(appConfig, "backend", "port", 8000, ["BACKEND_PORT"]);
const frontendHost = configValue(appConfig, "frontend", "host", "127.0.0.1", ["FRONTEND_HOST"]);
const frontendPort = intConfigValue(appConfig, "frontend", "port", 5173, ["FRONTEND_PORT"]);

export default defineConfig({
  plugins: [react()],
  server: {
    host: frontendHost,
    port: frontendPort,
    proxy: {
      "/api": `http://${backendHost}:${backendPort}`
    }
  }
});
