# DB Sentinel Agent 一页参赛摘要

_Hackathon 提交摘要，用于报名表、评审预读和项目首页简介。_

---

![DB Sentinel Agent 系统总览](assets/system-overview.svg)
_Figure 1: DB Sentinel Agent 把业务问数、SQL 安全校验、只读执行和审计解释串成一个闭环。_

![工作台查询结果截图](assets/screenshots/gmv-result.png)
_Figure 2: 实际工作台会同时展示问题、SQL、结果图表、表格和审计证据。_

## 📋 项目一句话

DB Sentinel Agent 是一个面向业务数据分析值班场景的只读数据库 Agent。业务同学用自然语言问数，Agent 自动读取 schema、生成查询计划和只读 SQL、先做安全校验、再执行查询，并返回表格、图表、业务解释和审计轨迹。

## 🎯 解决什么问题

| 真实问题 | 现在的痛点 | DB Sentinel Agent 的做法 |
| --- | --- | --- |
| 临时问数多 | 业务同学反复找数据分析师 | 直接在工作台提问 |
| SQL 口径散 | 聊天记录里难复核 | 展示 SQL、指标口径和时间窗 |
| 安全风险高 | Agent 可能生成写库 SQL | `sql_guard` 只允许 `SELECT` / `WITH` |
| 结果难解释 | 只给表格，业务还要追问 | 同时给图表、解释和下一步建议 |
| 过程无留痕 | 查过什么、为什么查不清 | 每次会话保存审计轨迹 |

## 📊 当前可演示能力

![Agent 六步闭环](assets/agent-workflow.svg)
_Figure 3: 每次问答固定经过六个可审计步骤。_

- 渠道 GMV 排名：最近 7 天哪个渠道 GMV 最高。
- 转化异常定位：哪个渠道转化率下降最多，可能原因是什么。
- 活动 ROI 复盘：618 活动期间 ROI 最好的渠道是哪几个。
- 售后风险发现：最近一周退款率异常升高的商品类别。
- 新用户分析：不同城市新用户首单转化差异。
- 安全拦截：危险写库请求会被拒绝，不执行 SQL。

## 🔐 为什么可信

![只读安全防线](assets/safety-shield.svg)
_Figure 4: 安全边界不是提示词约束，而是 SQL AST 校验和只读数据库连接。_

- SQL AST 解析：用 `sqlglot` 解析 SQL，不靠字符串猜测。
- 单语句限制：拒绝多语句执行。
- 只读白名单：只允许 `SELECT` / `WITH`。
- 业务表白名单：拒绝 SQLite 内部表、pragma 和未授权表。
- 危险操作拦截：拒绝 `INSERT`、`UPDATE`、`DELETE`、`DROP`、危险函数和高风险函数。
- 只读执行层：SQLite 连接使用 `mode=ro`，并开启 `PRAGMA query_only=ON`。

![危险请求拦截图](assets/screenshots/safety-block.png)
_Figure 5: 危险请求会停在 guard 层，不进入数据库执行。_

## 📈 参赛亮点

![价值地图](assets/value-map.svg)
_Figure 6: 同一个 Agent 闭环同时提升业务效率、数据团队效率、治理安全和工程扩展性。_

| 维度 | 亮点 |
| --- | --- |
| 业务价值 | 业务同学可以自助完成常见经营分析 |
| 工作流价值 | 从“找人写 SQL”变成“Agent 值班闭环” |
| 安全价值 | 只读边界可检查、可演示、可验证 |
| 数据价值 | SQL、口径、结果和解释都能复核 |
| 工程价值 | 可扩展到真实只读连接器、指标语义层、权限系统 |

## 🔧 技术栈

- Frontend：React + Vite + TypeScript + Recharts
- Backend：FastAPI + Python
- DB：内置 SQLite 示例业务库
- SQL Guard：`sqlglot` AST 解析
- Config：`config/app.conf` 统一管理 URL、API、端口和 DB 路径
- LLM：OpenAI-compatible client，可配置 `.env`
- Fallback：无 LLM key 时仍可稳定演示内置样例
- Tests：pytest、Vite build、Playwright 浏览器验收

## 🎬 3 分钟演示路径

![3 分钟演示故事线](assets/demo-storyboard.svg)
_Figure 7: 演示按业务价值、异常洞察和安全边界展开。_

1. 点击“最近 7 天 GMV 最高的渠道是什么？”
2. 展示 schema、Agent 计划、SQL、guard、图表、表格和回答。
3. 点击“哪个渠道转化率下降最多，可能原因是什么？”
4. 展示异常定位和业务解释。
5. 输入“帮我 drop table orders”。
6. 展示只读安全拦截，不执行 SQL。

## 📌 当前边界

当前 Demo 使用内置 SQLite 示例库，不连接生产数据库。它证明的是“只读、安全、可审计的数据分析 Agent 工作流”成立。生产化前需要补企业鉴权、真实数据库只读连接器、指标语义层、查询成本控制、结果脱敏和审计落库。

它是一个垂直 Agent 应用，不是 CC / Hermes 级别的通用 agent 平台；参赛叙事重点应放在“Agent 重塑数据分析值班工作流”。

## 🔗 相关文档

- [参赛文档](COMPETITION_SUBMISSION.md)
- [演示指南](DEMO_GUIDE.md)
- [PPT 路演大纲](PITCH_DECK_OUTLINE.md)
- [演示视频脚本](VIDEO_SCRIPT.md)
- [技术架构说明](ARCHITECTURE.md)
- [配置说明](CONFIGURATION.md)
- [参赛提交清单](SUBMISSION_CHECKLIST.md)
- [评委问答](JUDGE_QA.md)
