# OfferPilot MCP 项目评估

评估日期：2026-08-13

## 结论

OfferPilot 当前已达到可用于作品集、项目答辩和 AI 应用开发实习面试演示的阶段。它不是单纯的 CRUD 或爬虫项目：系统已经形成公开岗位采集、结构化抽取、用户画像、岗位匹配、面试训练、Agent 编排、Text2SQL、SQL Guard、Tool Registry、Skills、Trace 和远程 MCP Server 的完整业务闭环。

当前不应描述为生产级平台。主要差距集中在数据质量、LLM 在线评估、MCP 分页与授权体系，而不是缺少更多页面或工具。

## 评估结果

| 维度 | 评分 | 判断依据 |
| --- | ---: | --- |
| 业务闭环 | 88/100 | 采集、分析、画像、匹配、面试和学习计划链路已经存在 |
| MCP 实现 | 82/100 | 官方 SDK、Streamable HTTP、5个只读 Tool、1个 Resource、鉴权、限流和审计已上线验证 |
| Agent 工程化 | 80/100 | 7个 Skill、Router、Planner、Executor、工具白名单、Trace 和规则回退完整 |
| 后端与安全 | 80/100 | FastAPI/MySQL 分层、用户归属、SSRF 防护、SQL AST Guard 和错误处理较完整 |
| 数据质量 | 62/100 | 真实岗位已入库，但部分正文含导航噪声，部分岗位要求和技能尚未抽取 |
| 测试与评估 | 76/100 | 70项测试和50项离线评估通过；尚缺覆盖率、固定模型在线评估和人工业务评分结果 |
| 生产准备度 | 58/100 | 已部署 Render + TiDB，但仍是静态 Token、单实例限流，缺少分页、共享限流和生产监控 |

综合判断：约80/100，属于完成度较高的实习作品集项目，但距离生产级系统仍有明确边界。

## 已验证证据

- `python -m unittest discover -s tests -q`：70项测试通过。
- `python -m eval.run_evaluations --write-report`：50/50项确定性评估通过。
- `node --check frontend/app.js`：前端 JavaScript 语法通过。
- Render `/health`：生产环境、TiDB 和 LLM 配置可用。
- MCP Inspector：线上 `tools/list`、`tools/call`、`resources/list` 和 `resources/read` 已成功。
- MCP 当前公开5个只读 Tool，并提供 `offerpilot://skills/catalog` Resource。

## 本次评估发现并修复的问题

1. “适合我的画像”此前错误回退到岗位查询，现已纳入 `profile-match` 规则。
2. Text2SQL 规则兜底此前不支持“岗位类型统计”和“出现次数最多的N项技能”，现已补齐。
3. SQL Guard 在组合筛选中把逻辑 `AND` 误判为未授权函数，现已修复并增加回归测试。

## 主要剩余风险

### 中风险

1. `search_jobs` 返回完整岗位列表。线上数据已经较多，MCP 返回内容过长，容易占用 Host 上下文；需要增加过滤、分页和硬性上限。
2. 通用爬虫正文包含导航、登录入口和站点推广文字，会干扰技能抽取与面试题生成；需要做站点级正文选择器或噪声清洗。
3. 部分真实岗位的 `skills` 为空、`requirement_json` 为 `null`。系统能诚实返回空状态，但画像匹配和面试质量依赖批量抽取完成度。
4. LLM Router、Planner、JD 抽取和面试题生成目前有规则兜底，但尚未在固定模型和固定数据集下测量准确率、稳定性、延迟和成本。

### 低风险或演示边界

1. MCP 使用静态 Bearer Token，适合当前单用户作品集部署，不适合多租户生产授权。
2. 限流保存在单实例内存中，扩容后各实例不会共享计数。
3. MCP 尚未提供 Prompt；这不影响 Tool Server 成立，但协议能力展示还可继续扩展。
4. 项目中仍有若干空的早期占位模块。当前运行路径未引用它们，但提交前应逐个确认后删除或补充说明，避免面试官误认为架构未收尾。

## 下一阶段建议

优先完成数据质量治理，而不是继续增加 Tool 数量：先为岗位正文去噪，再批量补齐技能和结构化要求，随后建立固定模型下的线上评估。完成后再做 MCP 查询分页和 Prompt。这样能直接改善岗位匹配、面试题和学习计划三个下游功能。
