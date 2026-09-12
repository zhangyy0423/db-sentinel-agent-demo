import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Database,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  TableProperties
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { browserApiDisplay, fetchAudit, fetchConfig, fetchSchema, resetDemo, sendQuestion } from "./api";
import type { AgentStep, AppConfig, AuditRecord, ChatResponse, SchemaResponse } from "./types";

type ChatEntry =
  | { role: "user"; content: string }
  | { role: "agent"; content: ChatResponse };

const dangerousPrompts = ["帮我 drop table orders", "把最近 7 天订单金额 update 成 0"];
const chartColors = ["#0f766e", "#2563eb", "#d97706", "#be123c"];

function App() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [appConfig, setAppConfig] = useState<AppConfig | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("最近 7 天 GMV 最高的渠道是什么？");
  const [activeResult, setActiveResult] = useState<ChatResponse | null>(null);
  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then(setAppConfig)
      .catch(() => setAppConfig(null));
    fetchSchema()
      .then(setSchema)
      .catch((err: Error) => setError(err.message));
  }, []);

  const totalRows = useMemo(
    () => schema?.tables.reduce((sum, table) => sum + table.row_count, 0) ?? 0,
    [schema]
  );

  async function runQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setInput(trimmed);
    setActiveResult(null);
    setAuditRecords([]);
    setPendingQuestion(trimmed);
    setEntries((current) => [...current, { role: "user", content: trimmed }]);
    try {
      const response = await sendQuestion(trimmed);
      setEntries((current) => [...current, { role: "agent", content: response }]);
      setActiveResult(response);
      try {
        const audit = await fetchAudit(response.session_id);
        setAuditRecords(audit);
      } catch (err) {
        setError(err instanceof Error ? `审计记录读取失败：${err.message}` : "审计记录读取失败");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
      setPendingQuestion(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runQuestion(input);
  }

  async function handleReset() {
    if (!appConfig?.database.resetEnabled) {
      setError("当前配置未开放 demo reset。需要本地重置时，将 config/app.conf 的 reset_enabled 改为 true。");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await resetDemo();
      const nextSchema = await fetchSchema();
      setSchema(nextSchema);
      setAuditRecords([]);
      setEntries([]);
      setActiveResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "重置失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Database size={22} aria-hidden="true" />
          </div>
          <div>
            <h1>DB Sentinel Agent</h1>
            <p>业务数据分析值班 · 只读 SQLite Demo</p>
          </div>
        </div>
        <div className="status-strip">
          <span className="status-pill">
            <ShieldCheck size={16} aria-hidden="true" />
            只读模式
          </span>
          <span className="status-pill">
            <CheckCircle2 size={16} aria-hidden="true" />
            SQL Guard
          </span>
          <span className="status-pill muted">
            {schema?.business_date ?? "2026-06-18"}
          </span>
          <span className="status-pill muted" title="当前前端请求的 API 地址">
            API: {appConfig?.apiDisplay ?? browserApiDisplay()}
          </span>
          <button
            className="icon-button"
            onClick={handleReset}
            disabled={!appConfig?.database.resetEnabled || loading}
            title={
              appConfig?.database.resetEnabled
                ? "重置示例数据库"
                : "reset 默认关闭，可在 config/app.conf 中开启"
            }
          >
            <RefreshCw size={17} aria-hidden="true" />
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="schema-panel panel">
          <PanelTitle icon={<TableProperties size={18} />} title="Schema" />
          <div className="db-meta">
            <span>{schema?.database ?? "loading"}</span>
            <strong>{totalRows.toLocaleString()} rows</strong>
          </div>
          <div className="table-list">
            {schema?.tables.map((table) => (
              <section className="schema-table" key={table.name}>
                <div className="schema-table-head">
                  <strong>{table.name}</strong>
                  <span>{table.row_count}</span>
                </div>
                <p>{table.description}</p>
                <div className="column-list">
                  {table.columns.map((column) => (
                    <span key={`${table.name}.${column.name}`} title={column.description}>
                      {column.name}
                    </span>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="prompt-bank">
            <h2>样例问题</h2>
            {schema?.sample_questions.map((question) => (
              <button key={question} onClick={() => runQuestion(question)} disabled={loading}>
                <Play size={15} aria-hidden="true" />
                <span>{question}</span>
              </button>
            ))}
          </div>

          <div className="prompt-bank compact">
            <h2>安全演示</h2>
            {dangerousPrompts.map((question) => (
              <button key={question} onClick={() => runQuestion(question)} disabled={loading}>
                <AlertTriangle size={15} aria-hidden="true" />
                <span>{question}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="conversation-panel panel">
          <PanelTitle icon={<Bot size={18} />} title="Agent Console" />

          <div className="conversation-scroll">
            {entries.length === 0 ? (
              <div className="empty-state">
                <Bot size={34} aria-hidden="true" />
                <strong>值班 Agent 待命</strong>
                <span>schema_retrieve → intent_plan → sql_guard → reflect_and_answer</span>
              </div>
            ) : (
              entries.map((entry, index) =>
                entry.role === "user" ? (
                  <div className="message user-message" key={`${entry.role}-${index}`}>
                    {entry.content}
                  </div>
                ) : (
                  <AgentMessage
                    response={entry.content}
                    onRunSuggestion={runQuestion}
                    disabled={loading}
                    key={`${entry.role}-${index}`}
                  />
                )
              )
            )}
          </div>

          {error ? <div className="error-banner">{error}</div> : null}

          <form className="input-row" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="输入业务数据问题"
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              <Send size={17} aria-hidden="true" />
              <span>{loading ? "分析中" : "发送"}</span>
            </button>
          </form>
        </section>

        <aside className="insight-panel panel">
          <PanelTitle icon={<ShieldCheck size={18} />} title="Result & Audit" />
          {loading && pendingQuestion ? (
            <PendingResult question={pendingQuestion} />
          ) : activeResult ? (
            <>
              <GuardBanner response={activeResult} />
              <EvidenceSummary response={activeResult} />
              <ResultChart response={activeResult} />
              <ResultTable response={activeResult} />
              <AuditTrail steps={activeResult.steps} records={auditRecords} />
            </>
          ) : (
            <div className="empty-result">
              <Database size={30} aria-hidden="true" />
              <span>暂无查询结果</span>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

function PendingResult({ question }: { question: string }) {
  return (
    <div className="pending-result">
      <Bot size={28} aria-hidden="true" />
      <strong>正在分析当前问题</strong>
      <span>{question}</span>
      <small>右侧结果已清空，等待本次 SQL guard 和执行结果。</small>
    </div>
  );
}

function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function AgentMessage({
  response,
  onRunSuggestion,
  disabled
}: {
  response: ChatResponse;
  onRunSuggestion: (question: string) => void;
  disabled: boolean;
}) {
  return (
    <article className={`message agent-message ${response.blocked ? "blocked" : ""}`}>
      <div className="answer-text">{response.answer}</div>
      <div className="step-grid">
        {response.steps.map((step) => (
          <StepItem key={step.name} step={step} />
        ))}
      </div>
      <pre className="sql-block">{response.sql}</pre>
      {response.suggestions.length ? (
        <div className="suggestions">
          {response.suggestions.map((suggestion) => (
            <button
              type="button"
              key={suggestion}
              disabled={disabled}
              onClick={() => onRunSuggestion(suggestion)}
              title="继续追问"
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function StepItem({ step }: { step: AgentStep }) {
  const blocked = step.status === "blocked";
  return (
    <div className={`step-item ${blocked ? "blocked" : ""}`}>
      {blocked ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
      <div>
        <strong>{step.name}</strong>
        <span>{step.summary}</span>
      </div>
    </div>
  );
}

function GuardBanner({ response }: { response: ChatResponse }) {
  return (
    <div className={`guard-banner ${response.guard.allowed ? "allowed" : "denied"}`}>
      {response.guard.allowed ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
      <span>{response.guard.reason}</span>
    </div>
  );
}

function EvidenceSummary({ response }: { response: ChatResponse }) {
  const items = [
    ["session_id", response.session_id],
    ["guard", response.guard.allowed ? "allowed" : "blocked"],
    ["row_count", String(response.row_count ?? response.rows.length)],
    ["sql_source", response.sql_source || response.generated_by],
    ["reason", response.guard.reason]
  ];

  return (
    <section className="result-block">
      <h3>执行证据</h3>
      <div className="evidence-grid">
        {items.map(([label, value]) => (
          <div className="evidence-item" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ResultChart({ response }: { response: ChatResponse }) {
  if (!response.chart || !response.rows.length) {
    return null;
  }

  return (
    <section className="result-block">
      <h3>{response.chart.title}</h3>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height={240}>
          {response.chart.type === "line" ? (
            <LineChart data={response.rows} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey={response.chart.xKey} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              {response.chart.yKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={chartColors[index % chartColors.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          ) : (
            <BarChart data={response.rows} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey={response.chart.xKey} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              {response.chart.yKeys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={chartColors[index % chartColors.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function ResultTable({ response }: { response: ChatResponse }) {
  if (!response.columns.length) {
    return null;
  }

  return (
    <section className="result-block">
      <h3>结果表格</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {response.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {response.rows.slice(0, 20).map((row, rowIndex) => (
              <tr key={rowIndex}>
                {response.columns.map((column) => (
                  <td key={column}>{formatCell(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AuditTrail({ steps, records }: { steps: AgentStep[]; records: AuditRecord[] }) {
  return (
    <section className="result-block">
      <h3>审计轨迹</h3>
      <div className="audit-list">
        {steps.map((step, index) => (
          <div className="audit-item" key={step.name}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{step.name}</strong>
              <p>{step.summary}</p>
            </div>
          </div>
        ))}
        {records.map((record) => (
          <details className="audit-record" key={`${record.kind}-${record.ts ?? ""}`}>
            <summary>
              <span>{record.kind}</span>
              <small>{record.ts ? formatTimestamp(record.ts) : "no timestamp"}</small>
            </summary>
            <pre>{JSON.stringify(record.payload, null, 2)}</pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", { hour12: false });
}

function formatCell(value: string | number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? value : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value;
}

export default App;
