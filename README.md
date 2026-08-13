---
title: OfferPilot MCP
sdk: docker
app_port: 7860
pinned: false
---

# OfferPilot MCP

OfferPilot MCP 是一个面向 AI、软件开发和技术岗位求职者的智能岗位管理与分析工作台。

项目当前定位是：

- 面向用户：采集真实岗位、抽取岗位要求、建立简历画像、分析岗位匹配、生成模拟面试问题。
- 面向开发者与面试展示：展示 Tool Registry、Text2SQL、SQL Guard、Agent Trace 和工具调用日志。

> 说明：当前项目已使用官方 MCP Python SDK 提供 Streamable HTTP Endpoint，并开放第一批只读岗位工具。远程 Endpoint 使用静态 Bearer Token、基础限流和调用审计；这适合当前单用户演示部署，但不等同于完整 OAuth 2.1 授权服务器。

## 当前功能

### 岗位采集

- 支持公开岗位 URL 单条采集。
- 支持公开岗位 URL 批量采集。
- 自动解析岗位标题、公司、城市、岗位类型、岗位描述和来源链接。
- 采集边界：只处理无需登录、公开可访问的岗位详情页；不处理验证码、登录态和受限页面。
- 采集前校验 URL、DNS 和目标 IP，阻止本机、私网、链路本地地址和云元数据地址。
- 关闭自动重定向并逐跳重新校验，限制为标准 HTTP/HTTPS 端口、最多5次跳转和5 MB响应体。

### 岗位管理

- 支持新增岗位。
- 支持岗位列表查询。
- 支持岗位详情查看。
- 支持按岗位内容抽取技能和要求。

### 技能与要求抽取

- 优先由 LLM 从岗位原文中抽取技能和结构化要求，模型不可用时使用规则兜底。
- 抽取学历、英语、专业、经验、项目经历、职责和软能力等岗位要求。
- LLM 抽取项必须携带 JD 原文证据，无法在原文中验证的技能和要求会被丢弃。
- 技能类别、重要性和输出数量经过代码校验，避免模型结果直接污染技能库。
- 技能写入 `skills` 和 `job_skills`。
- 重复抽取会同步替换岗位技能关联，避免保留过期标签。
- 结构化要求写入 `jobs.requirement_json`。
- 管理员批量抽取时按岗位逐条显示进度，并区分“已提取技能”“仅岗位要求”和“失败”；每条完成后即时更新前端状态，批次结束后再与数据库校准。

### 用户画像

- 支持创建用户画像。
- 支持上传 PDF / DOCX 简历并提取画像。
- 简历解析优先使用 LLM，失败时使用规则兜底。
- 不保存原始简历文件，仅保存结构化画像结果。

### 匹配分析

- 根据用户画像和岗位要求计算匹配结果。
- 展示已满足技能、缺失技能、匹配分数和补充建议。
- 普通用户可在匹配中心直接生成学习计划，查看技能优先级、涉及岗位数量、真实岗位示例和行动建议。

### Text2SQL

- 支持自然语言查询岗位数据。
- 优先由 LLM 根据真实 MySQL Schema 生成 SQL，模型不可用时回退到规则查询。
- 使用 SQLGlot 将 SQL 解析为 AST，再由 SQL Guard 校验允许的表、字段、函数和查询结构。
- 首次 SQL 未通过 Guard 时，允许模型根据拒绝原因自修复一次；修复后仍不安全则拒绝执行。
- 禁止非 SELECT、系统表、隐私表、危险函数、多语句、子查询和跨 Schema 查询。
- 查询最多返回100行，前端和 Agent Trace 会展示 `llm`、`llm_repaired` 或 `rules_fallback` 生成模式。

### Agent 与工具调用

- Agent Router 优先使用 LLM 理解自然语言任务，并只允许路由到已注册 Skill；模型不可用、结果非法、置信度低或缺少必要参数时使用规则兜底。
- 当前支持7个可执行 Skill：
  - `job-search`
  - `jd-crawl`
  - `jd-analysis`
  - `profile-match`
  - `mock-interview`
  - `answer-evaluator`
  - `study-plan`
- `.skills/*/SKILL.md` 会被解析为结构化执行约束，包括触发关键词、执行步骤、允许工具、质量检查和失败处理。
- Executor 在每次工具调用前检查当前 Skill 的工具白名单，禁止跨 Skill 调用未授权工具。
- 支持 Tool Registry：
  - `search_jobs`
  - `get_job_detail`
  - `get_job_requirements`
  - `list_skills`
  - `text2sql_query`
  - `crawl_job_url`
  - `extract_skills`
  - `match_my_profile`
  - `generate_my_mock_interview`
  - `evaluate_my_interview_answer`
  - `generate_my_study_plan`
- Agent Trace 会记录路由方式、置信度、Skill 执行步骤、工具白名单、输入输出和调用编号；Tool Call Log 记录真实工具执行结果。
- Agent Planner 会在白名单范围内生成最多3步的最小计划。当前支持“采集公开 URL 后，按用户明确要求继续抽取该岗位技能”的真实两步链路；后续步骤只读取前一步真实输出中的 `job_id`。
- 支持官方 MCP Streamable HTTP Endpoint：`/mcp/`。
- 支持只读 MCP Resource：`offerpilot://skills/catalog`，用于向 MCP Host 提供真实岗位技能目录上下文。
- 当前通过 MCP 暴露5个只读工具：
  - `search_jobs`
  - `get_job_detail`
  - `get_job_requirements`
  - `list_skills`
  - `text2sql_query`
- 爬虫、画像和面试等涉及写入或用户数据的能力暂不通过 MCP 对外开放。
- `/agent/run` 面向已登录用户开放；画像匹配与模拟面试工具只从服务端认证上下文取得当前用户可访问的画像，任务文本不能指定其他用户画像。
- 学习计划只按真实岗位匹配结果中的缺失技能频次排序，并保留关联岗位示例；不编造课程、认证、学习时长或就业结果。

### 模拟面试

- 基于岗位信息生成模拟面试问题。
- 支持回答评价。
- 当前以工程可解释的规则和结构化数据为主，后续可增强为更完整的 LLM 面试官。

## 技术栈

### 后端

- Python
- FastAPI
- MySQL 8.x
- PyMySQL
- Pydantic
- OpenAI-Compatible LLM API / OpenRouter
- MCP Python SDK 2.0
- BeautifulSoup / Requests
- PDF / DOCX 文本解析依赖

### 前端

- 原生 HTML
- CSS
- JavaScript
- 后端通过 FastAPI StaticFiles 在根路径 `/` 提供前端页面

当前没有使用 React、Vue 或 Next.js。

## 目录结构

```text
offerpilot-mcp/
├── backend/
│   ├── agent/              # Agent 路由、执行、Trace
│   ├── crawler/            # 公开岗位页面采集与解析
│   ├── db/                 # MySQL 初始化和 schema
│   ├── repositories/       # 数据访问层
│   ├── routers/            # FastAPI 路由
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── services/           # 业务逻辑
│   ├── tools/              # Tool Registry 和工具执行
│   ├── mcp_server.py       # 官方 MCP Server 与现有工具的适配层
│   ├── config.py           # 环境变量配置
│   └── main.py             # FastAPI 应用入口
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── eval/
│   ├── run_evaluations.py          # 离线确定性评估入口
│   ├── *_eval_cases.json           # 路由、SQL、爬虫评估用例
│   ├── latest_report.json          # 机器可读评估结果
│   └── latest_report.md            # 可展示评估报告
├── tests/                          # 自动化回归测试
├── PROJECT_ASSESSMENT.md           # 当前项目完成度与风险评估
├── .env.example
├── requirements.txt
├── AGENTS.md
└── README.md
```

## 数据库

当前使用 MySQL。

默认数据库名：

```text
offerpilot_mcp
```

主要数据表：

| 表名 | 作用 |
| --- | --- |
| `companies` | 公司信息 |
| `jobs` | 岗位信息、岗位描述、结构化要求 |
| `skills` | 技能词库 |
| `job_skills` | 岗位与技能关联 |
| `tool_call_logs` | 工具调用记录 |
| `agent_traces` | Agent 执行轨迹 |
| `user_profiles` | 用户画像 |
| `interview_sessions` | 模拟面试记录 |
| `answer_evaluations` | 面试回答评价 |

## 环境变量

复制 `.env.example` 为 `.env`，并按本机环境填写。

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=offerpilot_app
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=offerpilot_mcp

LLM_API_KEY=your_api_key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=your_model

OPENROUTER_API_KEY=your_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=your_model

MCP_ACCESS_TOKEN=replace-with-a-long-random-token
MCP_RATE_LIMIT_REQUESTS=60
MCP_RATE_LIMIT_WINDOW_SECONDS=60
```

不要提交真实 `.env`、API Key、数据库密码、简历文件或私密岗位数据。

## 本地启动

在 Windows PowerShell 或 CMD 中：

```bat
conda.bat activate offerpilot
cd /d "D:\OfferPilot MCP\offerpilot-mcp"
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

访问：

```text
健康检查：http://127.0.0.1:8000/health
接口文档：http://127.0.0.1:8000/docs
前端页面：http://127.0.0.1:8000/
```

## 常用接口

```text
GET  /health
GET  /jobs
GET  /jobs/{job_id}
POST /jobs
POST /jobs/{job_id}/extract-skills
POST /jobs/extract-skills/batch
POST /jobs/extract-requirements/batch

POST /crawler/fetch-url
POST /crawler/fetch-urls
POST /crawler/import-json

GET  /skills
GET  /skills/workflows

POST /query/text2sql

GET  /tools
GET  /tools/logs
POST /tools/{tool_name}/call

POST /agent/route
POST /agent/run
GET  /agent/traces

POST /mcp/
GET  /mcp/
DELETE /mcp/

POST /profile
POST /profile/parse-resume
GET  /profile/{user_id}
GET  /profile/{user_id}/matches

POST /interview/mock
POST /interview/evaluate
```

## 本地验证

后端语法检查：

```bat
python -m compileall backend
```

前端 JavaScript 语法检查：

```bat
node --check frontend\app.js
```

全量单元与集成边界测试：

```bat
python -m unittest discover -s tests -q
```

离线确定性评估并生成报告：

```bat
python -m eval.run_evaluations --write-report
```

当前验证结果为80项自动化测试通过、84/84项离线确定性评估通过。其中 SQL Guard 覆盖25类常见只读查询和24类危险或无效查询；其余评估覆盖规则路由、Text2SQL 规则兜底、通用 HTML 解析器、Skill 资产完整性和 MCP Tool/Resource 注册。详细结果见 [`eval/latest_report.md`](eval/latest_report.md)。该结果不代表线上数据完整性或 LLM 生成质量。

接口联调建议顺序：

1. `GET /health`
2. `POST /crawler/fetch-url`
3. `GET /jobs`
4. `POST /jobs/{job_id}/extract-skills`
5. `POST /jobs/extract-requirements/batch`
6. `POST /profile/parse-resume`
7. `GET /profile/{user_id}/matches`
8. `POST /profile/study-plan`
9. `POST /query/text2sql`
10. `POST /agent/run`
11. `GET /agent/traces`

MCP Inspector 验证：

```bat
mcp dev backend\mcp_server.py:offerpilot_mcp
```

在 Inspector 中依次检查 Resource `offerpilot://skills/catalog`，以及 `search_jobs`、`get_job_detail`、`get_job_requirements`、`list_skills` 和 `text2sql_query`。通过 FastAPI 联调时，Streamable HTTP 地址为：

```text
http://127.0.0.1:8000/mcp/
```

远程或 FastAPI 挂载地址必须在每次请求中携带 Bearer Token。Inspector CLI 示例：

```bat
npx -y @modelcontextprotocol/inspector --cli http://127.0.0.1:8000/mcp/ --transport http --method tools/list --header "Authorization: Bearer your_mcp_token"
```

Token 只能放在 `Authorization` Header，不要拼接到 URL。`mcp dev` 直接加载 Server 对象进行本地调试，不经过 FastAPI 外层的 Token 中间件。

## 当前项目边界

当前已经能作为本地作品集演示版本使用，但还不等于生产级系统。

已具备：

- 真实 MySQL 存储。
- 真实公开 URL 采集。
- 技能和岗位要求抽取。
- 简历画像抽取。
- 岗位匹配分析。
- LLM Text2SQL、AST SQL Guard 和规则兜底。
- Agent 工具调用链路。
- 前端工作台。
- REST API 登录鉴权、管理员权限和用户画像归属校验。

仍需完善：

- 当前已有80项自动化测试和84项离线确定性评估，但尚未统计代码覆盖率，也未建立固定模型下的在线 LLM 评估基线。
- MCP 当前暴露只读岗位工具和技能目录 Resource，尚未实现 Prompts。
- 远程 MCP 已有静态 Bearer Token 和单实例内存限流，但尚未实现标准 OAuth 2.1、scope 和多实例共享限流。
- Skill Loader 已能发现7个本地 Skill，并约束允许工具和质量检查；Planner 的执行形状仍按 Skill 硬编码，尚未成为完全由 Skill 文件驱动的通用执行器。
- `search_jobs` 当前返回完整岗位列表，尚未提供 MCP 分页和过滤参数，真实数据增长后会占用较多上下文。
- 部分采集正文仍含页面导航等噪声，部分岗位尚未完成技能与结构化要求抽取，数据质量需要持续治理。
- 爬虫已具备应用层 SSRF 防护；生产环境仍应通过网络出口策略阻断内网和云元数据访问。
- 部署环境尚未做生产级安全加固。

当前完成度、证据与风险分级见 [`PROJECT_ASSESSMENT.md`](PROJECT_ASSESSMENT.md)。

## 部署上线流程

### 推荐方案一：云服务器部署

适合面试演示和作品集展示，控制力最强。

1. 准备一台云服务器，例如阿里云、腾讯云、华为云或海外 VPS。
2. 安装 Python 运行环境。
3. 安装或购买云 MySQL。
4. 创建数据库 `offerpilot_mcp` 和应用用户。
5. 上传项目代码到服务器。
6. 创建 `.env`，填写 MySQL 和 LLM 配置。
7. 安装依赖：

```bash
pip install -r requirements.txt
```

8. 启动后端：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

9. 使用 Nginx 反向代理到 8000 端口。
10. 配置 HTTPS。
11. 访问 `/health`、`/docs`、`/` 做冒烟测试。

### 推荐方案二：PaaS 部署

适合快速上线，例如 Render、Railway、Fly.io 等。

核心配置：

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

需要在平台环境变量中配置：

```text
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DATABASE
LLM_API_KEY 或 OPENROUTER_API_KEY
LLM_BASE_URL 或 OPENROUTER_BASE_URL
LLM_MODEL 或 OPENROUTER_MODEL
AUTH_SECRET_KEY
MCP_ACCESS_TOKEN
MCP_ALLOWED_HOSTS
MCP_ALLOWED_ORIGINS
```

生成 MCP Token：

```bat
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

将输出值保存为 Render 的 `MCP_ACCESS_TOKEN`，不要写进 Git。限流默认是单实例每个来源 IP 每 60 秒 60 次请求；如果以后扩容为多个实例，需要改成 Redis 等共享限流存储。

`/health` 中的 `llm_configured=true` 只表示环境变量中存在 API Key，不代表模型仍有可用额度。若简历解析提示 `LLM_RATE_LIMITED`，需要在模型服务商后台检查额度，等待重置或将 `OPENROUTER_MODEL` / `LLM_MODEL` 改为账户有权调用的模型；系统会保留规则解析结果作为降级输出。

注意：PaaS 上不要使用本机 MySQL，要使用云数据库。

### 推荐方案三：本地演示

如果暂时不想处理公网部署、数据库安全、API Key 暴露和爬虫合规问题，可以先用本地演示。

面试时可以展示：

- 本地前端页面。
- Swagger 接口文档。
- MySQL 表结构和真实数据。
- Agent Trace。
- Text2SQL SQL Guard。
- 简历上传画像提取。
- 岗位匹配和模拟面试。

本地演示的好处是稳定、安全、不会暴露真实 API Key 和简历数据。

## 面试表述建议

可以这样介绍项目：

> OfferPilot MCP 是我做的 AI 求职管理工作台。它从公开岗位页面采集真实 JD，写入 MySQL 后进行技能和岗位要求抽取，再结合用户简历画像做岗位匹配和模拟面试。后端用 FastAPI 分层实现，并通过官方 MCP Streamable HTTP 暴露只读工具；Tool Registry、SQL Guard、Agent Trace 和工具调用日志负责工具治理、安全检查与可观测性。

需要避免这样说：

> 我完整实现了官方 MCP 协议。

更稳妥的说法是：

> 当前版本使用官方 MCP Python SDK，通过 Streamable HTTP 暴露5个只读岗位工具和1个技能目录 Resource，并复用现有 Tool Registry、SQL Guard 和工具日志。远程入口加入静态 Bearer Token、基础限流和审计；完整 OAuth 2.1、写操作工具和 Prompts 仍在后续范围内。

## 下一步优先级

1. 清洗采集正文中的导航噪声，并批量补齐真实岗位的技能和结构化要求。
2. 为 `search_jobs` 增加过滤、分页和返回上限，控制 MCP 上下文体积。
3. 固定模型与 Prompt 版本，建立路由、技能抽取、面试题和回答评价的在线 LLM 评估集。
4. 根据部署规模决定是否升级 OAuth 2.1、共享限流和更完整的可观测性。
5. 再考虑新增 MCP Prompt，或进一步让 Skill 文件驱动通用 Planner。
