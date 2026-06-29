import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { configFile, configValue, readAppConfig, rootDir } from "./config.mjs";

const config = readAppConfig();
const runtimeConfigPath = resolve(
  rootDir,
  configValue(
    config,
    "frontend",
    "runtime_config_path",
    "public/runtime-config.js",
    ["FRONTEND_RUNTIME_CONFIG_PATH"]
  )
);
const apiBaseUrl = configValue(config, "frontend", "api_base_url", "", [
  "VITE_API_BASE_URL",
  "FRONTEND_API_BASE_URL"
]).replace(/\/$/, "");
const publicUrl = configValue(config, "app", "public_url", "http://127.0.0.1:5173", [
  "APP_PUBLIC_URL"
]);

const browserConfig = {
  apiBaseUrl,
  apiDisplay: apiBaseUrl || "same-origin /api",
  publicUrl,
  configFile: configFile.replace(`${rootDir}/`, "")
};

mkdirSync(dirname(runtimeConfigPath), { recursive: true });
writeFileSync(
  runtimeConfigPath,
  `window.__DB_SENTINEL_CONFIG__ = Object.freeze(${JSON.stringify(browserConfig, null, 2)});\n`,
  "utf8"
);

console.log(
  JSON.stringify(
    {
      configFile: browserConfig.configFile,
      runtimeConfig: runtimeConfigPath.replace(`${rootDir}/`, ""),
      apiDisplay: browserConfig.apiDisplay
    },
    null,
    2
  )
);
