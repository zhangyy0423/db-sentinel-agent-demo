# DB Sentinel Agent

面向 Hackathon 评审的 Web Demo：一个用于业务数据分析值班的只读数据库 Agent。Demo 内置 SQLite 示例业务库，覆盖用户、渠道、商品、订单、活动和行为事件数据。

![DB Sentinel Agent 系统总览](docs/assets/system-overview.svg)

## 文档导航

- [项目概览](docs/PROJECT_OVERVIEW.md)：先看这个，理解项目能做什么、不能做什么。
- [一页参赛摘要](docs/ONE_PAGER.md)：用于报名表、评审预读和项目首页简介。
- [参赛文档](docs/COMPETITION_SUBMISSION.md)：用于 Hackathon 报名、路演稿和评审材料。
- [PPT 路演大纲](docs/PITCH_DECK_OUTLINE.md)：用于制作 8 页展示 Deck。
- [演示视频脚本](docs/VIDEO_SCRIPT.md)：用于录制 2 到 3 分钟提交视频。
- [演示指南](docs/DEMO_GUIDE.md)：用于现场跑 Demo、讲解和排查问题。
- [配置说明](docs/CONFIGURATION.md)：说明上传后 URL、API、端口和数据库路径从哪里改。
- [参赛提交清单](docs/SUBMISSION_CHECKLIST.md)：提交前检查项、红队输入和截图要求。
- [评委问答](docs/JUDGE_QA.md)：准备现场 Q&A，避免过度承诺。
- [技术架构说明](docs/ARCHITECTURE.md)：用于开发交接和后续扩展。
- [文档索引](docs/README.md)：完整文档入口。

![DB Sentinel Agent 查询结果截图](docs/assets/screenshots/gmv-result.png)

## 核心闭环

Agent 每次回答都会保留 6 步审计轨迹：

![Agent 六步闭环](docs/assets/agent-workflow.svg)

1. `schema_retrieve`：读取表结构、字段说明和样例值。
2. `intent_plan`：拆解指标、过滤条件和时间范围。
3. `sql_generate`：命中内置数据分析问题时生成候选 SQL，无 LLM key 时使用规则 fallback。
4. `sql_guard`：用 `sqlglot` 解析 SQL，只允许单条 `SELECT` / `WITH`。
5. `execute_and_visualize`：只读执行 SQL，返回表格和图表建议。
6. `reflect_and_answer`：输出业务解释、异常洞察和下一步建议。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

启动后端：

```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

启动前端：

```bash
npm run dev
```

打开 `http://127.0.0.1:5173`。

## Agent Sandbox 单服务部署

云端部署时可以只暴露 FastAPI 一个服务。先构建前端：

```bash
npm run build
```

再启动后端托管 `dist/` 和 `/api/*`：

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Agent Sandbox 里只需要暴露 `8000` 端口。浏览器访问 Sandbox 分配的公网 URL 时，`GET /` 会返回前端页面，`GET /api/schema`、`POST /api/chat` 等接口继续由 FastAPI 提供。报名表的“可体验链接”填写 Sandbox 分配的公网根地址，例如 `https://<sandbox-domain>/`。

## 配置入口

统一配置文件在：

```text
config/app.conf
```

它控制前端 URL、后端端口、API base、SQLite 数据库路径和 reset 开关。上传作品或拆分部署时优先改这个文件；`npm run dev` 和 `npm run build` 会自动同步浏览器运行时配置到 `public/runtime-config.js`。

## LLM 配置

Demo 默认不依赖 LLM，未配置 key 时也能回答内置样例问题；无法识别或超出 Demo 范围的问题会返回边界说明，不会套用默认 GMV 模版。需要接入 OpenAI-compatible 模型时，复制 `.env.example` 为 `.env` 并填写：

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=...
```

配置模型后，LLM 会参与非数据分析问题的边界回复和后续可替换生成层；命中内置业务分析问题时，SQL 仍需经过只读 `sql_guard` 后才会执行。

## API

- `GET /api/schema`：返回表、字段、样例值、业务说明和样例问题。
- `GET /api/config`：返回当前公开 URL、API、数据库路径和 reset 开关。
- `POST /api/chat`：输入自然语言问题，返回 Agent 步骤、SQL、结果、图表配置和最终回答。
- `GET /api/audit/{session_id}`：返回会话审计记录。
- `POST /api/demo/reset`：重置示例数据库，默认关闭；需 `ENABLE_DEMO_RESET=true` 或 `config/app.conf` 显式开启。

## 验证

```bash
.venv/bin/pytest
npm run build
npm run qa:docs:images
```

启动前后端服务后可运行浏览器验收：

```bash
npm run qa:browser
npm run qa:docs:links
```

文档图片渲染验收：

```bash
npm run qa:docs:images
```

浏览器验收覆盖：

- 首页能看到 schema、样例问题、对话输入框。
- 点击样例问题能展示 SQL、结果表格、图表和最终解释。
- 危险请求展示只读安全拦截，不执行 SQL。
- 移动端宽度下文本不重叠。

浏览器验收会生成真实截图到 `docs/assets/screenshots/`，可直接用于参赛材料。
