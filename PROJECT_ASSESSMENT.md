# OfferPilot Agent 项目评估

评估日期：2026-08-21

## 结论

OfferPilot 当前已达到可用于作品集、项目答辩和 AI 应用开发实习面试演示的阶段。它不是单纯的 CRUD、爬虫或纯 MCP Server 项目：系统已经形成公开岗位采集、结构化抽取、用户画像、岗位匹配、面试训练、Agent 编排、Text2SQL、SQL Guard、Tool Registry、Skills、Trace 和远程 MCP Tool Server 的完整业务闭环。

当前更适合定义为“Agentic 求职分析系统 + MCP 工具出口”，不应描述为生产级平台。主要差距集中在数据质量、LLM 在线评估和生产级授权体系，而不是缺少更多页面或普通业务按钮。

## 评估结果

| 维度 | 评分 | 判断依据 |
| --- | ---: | --- |
| 业务闭环 | 88/100 | 采集、分析、画像、匹配、面试和学习计划链路已经存在 |
| MCP 实现 | 86/100 | 官方 SDK、Streamable HTTP、5个只读 Tool、1个 Resource、2个 Prompt、分页筛选、鉴权、限流和审计已具备 |
| Agent 工程化 | 80/100 | 7个 Skill、Router、Planner、Executor、工具白名单、Trace 和规则回退完整 |
| 后端与安全 | 80/100 | FastAPI/MySQL 分层、用户归属、SSRF 防护、SQL AST Guard 和错误处理较完整 |
| 数据质量 | 62/100 | 真实岗位已入库，但部分正文含导航噪声，部分岗位要求和技能尚未抽取 |
| 测试与评估 | 80/100 | 83项测试和86项离线评估通过；尚缺覆盖率、固定模型在线评估和人工业务评分结果 |
| 生产准备度 | 58/100 | 已部署 Render + TiDB，但仍是静态 Token、单实例限流，缺少分页、共享限流和生产监控 |

综合判断：约80/100，属于完成度较高的实习作品集项目，但距离生产级系统仍有明确边界。

## 已验证证据

- `python -m unittest discover -s tests -q`：83项测试通过。
- `python -m eval.run_evaluations --write-report`：86/86项确定性评估通过，其中 SQL Guard 覆盖49条安全与危险边界用例。
- `node --check frontend/app.js`：前端 JavaScript 语法通过。
- Render `/health`：生产环境、TiDB 和 LLM 配置可用。
- MCP Inspector：线上 `tools/list`、`tools/call`、`resources/list` 和 `resources/read` 已成功。
- MCP 当前公开5个只读 Tool、`offerpilot://skills/catalog` Resource 和2个 Prompt。

## 本次评估发现并修复的问题

1. “适合我的画像”此前错误回退到岗位查询，现已纳入 `profile-match` 规则。
2. Text2SQL 规则兜底此前不支持“岗位类型统计”和“出现次数最多的N项技能”，现已补齐。
3. SQL Guard 在组合筛选中把逻辑 `AND` 误判为未授权函数，现已修复并增加回归测试。
4. SQLGlot 的内部函数名曾导致 `YEAR()` 被误判，现改为按 MySQL 方言实际渲染出的函数名检查。
5. SQL Guard 现会拦截不属于当前查询表的字段、歧义字段、未知通配符别名、`SELECT INTO` 和超大 OFFSET。
6. MCP `search_jobs` 已增加关键词、城市、岗位类型、技能、抽取状态、分页和单次返回上限，避免完整岗位列表占用 Host 上下文。
7. MCP 已增加 `job_interview_prompt` 和 `skill_gap_study_plan_prompt`，用于展示 Prompt 能力并约束 Host 基于真实岗位工具工作。

## 主要剩余风险

### 中风险

1. 通用爬虫正文包含导航、登录入口和站点推广文字，会干扰技能抽取与面试题生成；需要做站点级正文选择器或噪声清洗。
2. 部分真实岗位的 `skills` 为空、`requirement_json` 为 `null`。系统能诚实返回空状态，但画像匹配和面试质量依赖批量抽取完成度。
3. LLM Router、Planner、JD 抽取和面试题生成目前有规则兜底，但尚未在固定模型和固定数据集下测量准确率、稳定性、延迟和成本。
4. MCP `search_jobs` 已有分页和上限，但尚未返回总命中数和排序参数；大数据量下还需要进一步控制查询解释和上下文摘要。

### 低风险或演示边界

1. MCP 使用静态 Bearer Token，适合当前单用户作品集部署，不适合多租户生产授权。
2. 限流保存在单实例内存中，扩容后各实例不会共享计数。
3. MCP Prompt 已提供第一版，但仍需在真实 Host 或 Inspector 中记录样例调用，证明 Host 能按 Prompt 正确调用工具。
4. 项目中仍有若干空的早期占位模块。当前运行路径未引用它们，但提交前应逐个确认后删除或补充说明，避免面试官误认为架构未收尾。

## 下一阶段建议

优先完成数据质量治理，而不是继续增加 Tool 数量：先为岗位正文去噪，再批量补齐技能和结构化要求，随后建立固定模型下的线上评估。MCP 分页和 Prompt 已补上，下一步应验证真实 Host 调用样例，并把结果沉淀到 README 或 eval 报告里。
