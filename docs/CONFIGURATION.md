# 配置说明

这份文档说明项目上传、换机器、换端口或拆分前后端部署时，应该改哪些配置。

## 统一配置入口

主配置文件：

```text
config/app.conf
```

它记录项目公开 URL、前端端口、后端端口、API base、数据库路径和 reset 开关。提交作品时，评审优先看这个文件，不需要翻代码找端口。

环境变量和 `.env` 可以覆盖 `config/app.conf`，适合临时部署或 CI：

```text
.env.example
```

优先级：

```text
环境变量 / .env > config/app.conf > 代码默认值
```

## 本地默认配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `app.public_url` | `http://127.0.0.1:5173` | 评审打开的前端地址 |
| `frontend.port` | `5173` | Vite 前端端口 |
| `frontend.api_base_url` | 空 | 空表示前端请求同源 `/api`，本地由 Vite proxy 转发 |
| `backend.port` | `8000` | FastAPI 后端端口 |
| `database.path` | `backend/data/db_sentinel_demo.sqlite3` | SQLite 示例库路径 |
| `database.reset_enabled` | `false` | 默认关闭数据库重置接口 |

## 上传或部署时怎么改 API 地址

### Agent Sandbox 单服务

Agent Sandbox / 云端体验链接建议使用单服务部署：Vite 先构建静态资源，FastAPI 同时托管前端页面和 `/api/*` 接口。

```bash
npm run build
.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Sandbox 只需要暴露 `8000` 端口。启动后访问 Sandbox 分配的公网根地址：

```text
https://<sandbox-domain>/
```

路由约定：

| 路径 | 行为 |
| --- | --- |
| `/api/schema`、`/api/chat`、`/api/audit/{session_id}` | FastAPI API |
| `/` | 返回 `dist/index.html` |
| `/assets/...`、`/runtime-config.js` | 返回 `dist/` 里的静态资源 |
| 其它非 `/api` 路径 | 回退到 `dist/index.html`，支持浏览器刷新 |

报名表的“可体验链接”填写 Sandbox 分配的公网根地址，不填 KU 知识库详情页。KU 页面只作为创意说明和材料入口。

单服务部署时保持：

```ini
[frontend]
api_base_url =
```

前端会同源请求 `/api`，不需要额外配置跨域。

如果前端和后端部署在同一个域名，保持：

```ini
[frontend]
api_base_url =
```

前端会请求同源 `/api/schema`、`/api/chat`、`/api/audit/...`。

如果前端静态站点和后端 API 分开部署，改成真实 API 域名：

```ini
[frontend]
api_base_url = https://your-api.example.com
```

然后同步浏览器运行时配置：

```bash
npm run sync:config
```

`npm run dev` 和 `npm run build` 会自动执行这个同步步骤。同步后的公开配置文件在：

```text
public/runtime-config.js
```

这个文件只包含公开 URL，不包含密钥。

## 后端启动地址

`config/app.conf` 里的后端配置：

```ini
[backend]
host = 127.0.0.1
port = 8000
cors_origins = http://127.0.0.1:5173,http://localhost:5173
```

本地启动：

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

如果后端端口改成 `8010`，需要同步改：

```ini
[backend]
port = 8010
```

前端开发代理会从 `vite.config.ts` 读取该端口。

## Reset 接口为什么默认关闭

项目叙事是“只读数据库 Agent”。因此：

```ini
[database]
reset_enabled = false
```

默认情况下：

```text
POST /api/demo/reset -> 403 demo reset disabled
```

本地演示前确实需要重置示例库时，可以临时开启：

```ini
[database]
reset_enabled = true
```

或使用环境变量：

```bash
ENABLE_DEMO_RESET=true .venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

提交作品时建议保持 `false`。

## LLM 配置

Demo 默认不依赖 LLM key。没有模型时，内置确定性 fallback 会稳定回答 5 个样例问题。

需要接 OpenAI-compatible 模型时，在 `.env` 里配置：

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=...
```

不要把真实 key 写入 `config/app.conf`、代码或文档；`.env` 保持本机或 Sandbox 私有配置。拿到 Sandbox 公网地址后，可以按需设置：

```bash
APP_PUBLIC_URL=https://<sandbox-domain>/
```

当前 Demo 的 SQL 仍使用确定性 fallback，模型调用只作为生成计划提示的可替换层。参赛时建议诚实表述为：

```text
当前版本证明 safe auditable workflow，fallback 保证现场稳定；LLM 是可替换生成层。
```

## 运行时自检接口

后端提供：

```text
GET /api/config
```

它会返回当前公开配置，例如：

```json
{
  "apiDisplay": "same-origin /api",
  "configFile": "config/app.conf",
  "database": {
    "name": "db_sentinel_demo.sqlite3",
    "mode": "readonly",
    "resetEnabled": false
  }
}
```

页面顶部也会展示当前 API 来源，方便评审确认前端连的是哪个后端。
