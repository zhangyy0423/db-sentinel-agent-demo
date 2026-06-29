# 文档索引

这组文档用于参赛提交、现场演示、代码交接和后续扩展。

![DB Sentinel Agent 系统总览](assets/system-overview.svg)

## 推荐阅读顺序

1. [项目概览](PROJECT_OVERVIEW.md)：先看这个，理解项目能做什么、不能做什么。
2. [一页参赛摘要](ONE_PAGER.md)：用于报名表、评审预读和项目首页简介。
3. [参赛文档](COMPETITION_SUBMISSION.md)：用于 Hackathon 报名、路演稿和评审材料。
4. [PPT 路演大纲](PITCH_DECK_OUTLINE.md)：用于制作 8 页展示 Deck。
5. [演示视频脚本](VIDEO_SCRIPT.md)：用于录制 2 到 3 分钟提交视频。
6. [演示指南](DEMO_GUIDE.md)：用于现场跑 Demo、讲解和排查问题。
7. [配置说明](CONFIGURATION.md)：用于上传、换端口、拆分部署和 API 地址配置。
8. [参赛提交清单](SUBMISSION_CHECKLIST.md)：用于提交前检查截图、验证和红队输入。
9. [评委问答](JUDGE_QA.md)：用于现场 Q&A。
10. [技术架构说明](ARCHITECTURE.md)：用于开发交接和后续扩展。

![查询结果截图](assets/screenshots/gmv-result.png)

## 最短版本

DB Sentinel Agent 是一个只读数据库分析值班 Agent。它让业务同学用自然语言问数，系统自动生成查询计划和只读 SQL，先做安全校验，再执行查询，并返回表格、图表、解释和审计轨迹。

它当前最适合演示：

- 渠道 GMV 排名
- 渠道转化率下降定位
- 618 活动 ROI 复盘
- 商品类别退款率异常发现
- 新用户首单转化城市差异
- 危险 SQL 只读安全拦截

## 视觉图资产

- [系统总览图](assets/system-overview.svg)
- [Agent 六步闭环图](assets/agent-workflow.svg)
- [只读安全防线图](assets/safety-shield.svg)
- [3 分钟演示故事线图](assets/demo-storyboard.svg)
- [价值地图](assets/value-map.svg)
- [工作台首屏截图](assets/screenshots/workbench.png)
- [GMV 查询结果截图](assets/screenshots/gmv-result.png)
- [危险请求拦截图](assets/screenshots/safety-block.png)
- [移动端截图](assets/screenshots/mobile-workbench.png)

## 参赛包装材料

- [一页参赛摘要](ONE_PAGER.md)
- [PPT 路演大纲](PITCH_DECK_OUTLINE.md)
- [演示视频脚本](VIDEO_SCRIPT.md)
- [配置说明](CONFIGURATION.md)
- [参赛提交清单](SUBMISSION_CHECKLIST.md)
- [评委问答](JUDGE_QA.md)
