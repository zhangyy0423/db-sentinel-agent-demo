import type {
  AppConfig,
  AuditRecord,
  BrowserRuntimeConfig,
  ChatResponse,
  SchemaResponse
} from "./types";

declare global {
  interface Window {
    __DB_SENTINEL_CONFIG__?: BrowserRuntimeConfig;
  }
}

function runtimeApiBaseUrl() {
  return (
    window.__DB_SENTINEL_CONFIG__?.apiBaseUrl?.trim() ||
    import.meta.env.VITE_API_BASE_URL?.trim() ||
    ""
  ).replace(/\/$/, "");
}

function apiUrl(path: string) {
  const baseUrl = runtimeApiBaseUrl();
  return baseUrl ? `${baseUrl}${path}` : path;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    let detail = "";
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      detail = parsed.detail || "";
    } catch {
      // Fall through to the raw response body when the server did not return JSON.
    }
    throw new Error(detail || text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function browserApiDisplay() {
  const runtimeDisplay = window.__DB_SENTINEL_CONFIG__?.apiDisplay?.trim();
  return runtimeDisplay || runtimeApiBaseUrl() || "same-origin /api";
}

export function fetchConfig(): Promise<AppConfig> {
  return request<AppConfig>("/api/config");
}

export function fetchSchema(): Promise<SchemaResponse> {
  return request<SchemaResponse>("/api/schema");
}

export function sendQuestion(question: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export async function fetchAudit(sessionId: string): Promise<AuditRecord[]> {
  const body = await request<{ records: AuditRecord[] }>(`/api/audit/${sessionId}`);
  return body.records;
}

export function resetDemo(): Promise<{ status: string; database: string }> {
  return request<{ status: string; database: string }>("/api/demo/reset", {
    method: "POST"
  });
}
