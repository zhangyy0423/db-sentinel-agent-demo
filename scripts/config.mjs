import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const configFile = resolve(rootDir, process.env.APP_CONFIG_FILE ?? "config/app.conf");

export function readAppConfig() {
  const sections = {};
  if (!existsSync(configFile)) {
    return sections;
  }

  let currentSection = "";
  for (const rawLine of readFileSync(configFile, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line.startsWith(";")) {
      continue;
    }
    if (line.startsWith("[") && line.endsWith("]")) {
      currentSection = line.slice(1, -1).trim();
      sections[currentSection] ??= {};
      continue;
    }
    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1 || !currentSection) {
      continue;
    }
    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    sections[currentSection][key] = value;
  }
  return sections;
}

export function configValue(config, section, key, fallback = "", envNames = []) {
  for (const envName of envNames) {
    if (Object.prototype.hasOwnProperty.call(process.env, envName)) {
      return process.env[envName] ?? "";
    }
  }
  return config[section]?.[key] ?? fallback;
}

export function intConfigValue(config, section, key, fallback, envNames = []) {
  const rawValue = configValue(config, section, key, String(fallback), envNames);
  const parsed = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}
