export type SchemaColumn = {
  name: string;
  type: string;
  description: string;
  sample_values: Array<string | number>;
};

export type SchemaTable = {
  name: string;
  description: string;
  row_count: number;
  columns: SchemaColumn[];
};

export type SchemaResponse = {
  database: string;
  mode: string;
  business_date: string;
  tables: SchemaTable[];
  sample_questions: string[];
};

export type AgentStep = {
  name: string;
  status: "completed" | "blocked" | string;
  summary: string;
  details: Record<string, unknown>;
};

export type ChartConfig = {
  type: "bar" | "line";
  title: string;
  xKey: string;
  yKeys: string[];
};

export type ChatResponse = {
  session_id: string;
  question: string;
  steps: AgentStep[];
  sql: string;
  guard: {
    allowed: boolean;
    reason: string;
    normalized_sql: string | null;
  };
  columns: string[];
  rows: Array<Record<string, string | number | null>>;
  chart: ChartConfig | null;
  answer: string;
  suggestions: string[];
  blocked: boolean;
  generated_by: string;
  sql_source: string;
  row_count: number;
};

export type AuditRecord = {
  kind: string;
  ts?: string;
  payload: Record<string, unknown>;
};

export type AppConfig = {
  appName: string;
  publicUrl: string;
  apiBaseUrl: string;
  apiDisplay: string;
  configFile: string;
  backend: {
    host: string;
    port: number;
  };
  database: {
    name: string;
    path: string;
    mode: string;
    resetEnabled: boolean;
  };
};

export type BrowserRuntimeConfig = Partial<Pick<AppConfig, "apiBaseUrl" | "apiDisplay" | "publicUrl">>;
