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

> 说明：当前项目已使用官方 MCP Python SDK 提供 Streamable HTTP Endpoint，并开放第一批只读岗位工具。现阶段仍是最小 MCP Server，尚未开放写操作工具、MCP 鉴权、Resources 和 Prompts。

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

- 从岗位描述中抽取技能。
- 从岗位描述中抽取结构化要求，例如学历、英语、专业、经验、项目经历等。
- 技能写入 `skills` 和 `job_skills`。
- 结构化要求写入 `jobs.requirement_json`。

### 用户画像

- 支持创建用户画像。
- 支持上传 PDF / DOCX 简历并提取画像。
- 简历解析优先使用 LLM，失败时使用规则兜底。
- 不保存原始简历文件，仅保存结构化画像结果。

### 匹配分析

- 根据用户画像和岗位要求计算匹配结果。
- 展示已满足技能、缺失技能、匹配分数和补充建议。

### Text2SQL

- 支持自然语言查询岗位数据。
- 通过 SQL Guard 限制只读查询。
- 禁止非 SELECT、危险关键字和多语句执行。

### Agent 与工具调用

- 支持 Agent 路由：
  - `job-search`
  - `jd-crawl`
  - `jd-analysis`
- 支持 Tool Registry：
  - `search_jobs`
  - `list_skills`
  - `text2sql_query`
  - `crawl_job_url`
  - `extract_skills`
- 支持 Agent Trace 和 Tool Call Log，便于调试和面试展示。
- 支持官方 MCP Streamable HTTP Endpoint：`/mcp/`。
- 当前通过 MCP 暴露3个只读工具：
  - `search_jobs`
  - `list_skills`
  - `text2sql_query`
- 爬虫、画像和面试等涉及写入或用户数据的能力暂不通过 MCP 对外开放。

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
│   └── cases/
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

接口联调建议顺序：

1. `GET /health`
2. `POST /crawler/fetch-url`
3. `GET /jobs`
4. `POST /jobs/{job_id}/extract-skills`
5. `POST /jobs/extract-requirements/batch`
6. `POST /profile/parse-resume`
7. `GET /profile/{user_id}/matches`
8. `POST /query/text2sql`
9. `POST /agent/run`
10. `GET /agent/traces`

MCP Inspector 验证：

```bat
mcp dev backend\mcp_server.py:offerpilot_mcp
```

在 Inspector 中依次检查 `search_jobs`、`list_skills` 和 `text2sql_query`。通过 FastAPI 联调时，Streamable HTTP 地址为：

```text
http://127.0.0.1:8000/mcp/
```

## 当前项目边界

当前已经能作为本地作品集演示版本使用，但还不等于生产级系统。

已具备：

- 真实 MySQL 存储。
- 真实公开 URL 采集。
- 技能和岗位要求抽取。
- 简历画像抽取。
- 岗位匹配分析。
- Text2SQL 只读查询保护。
- Agent 工具调用链路。
- 前端工作台。

仍需完善：

- 自动化测试覆盖不足。
- MCP 当前只暴露只读岗位工具，尚未实现远程 MCP 鉴权、Resources 和 Prompts。
- 登录和画像所有权已实现，但岗位写入、采集、Agent、工具日志等接口的权限控制仍需补齐。
- Skill Loader 已能发现本地 Skill，但 Skill 内容尚未真正驱动通用执行器。
- 爬虫已具备应用层 SSRF 防护；生产环境仍应通过网络出口策略阻断内网和云元数据访问。
- 部署环境尚未做生产级安全加固。
- Eval 结果需要整理为可展示报告。

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
```

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

> OfferPilot MCP 是我做的 AI 求职管理工作台。它从公开岗位页面采集真实 JD，写入 MySQL 后进行技能和岗位要求抽取，再结合用户简历画像做岗位匹配和模拟面试。后端用 FastAPI 分层实现，包含 Tool Registry、SQL Guard、Agent Trace 和工具调用日志，用来展示类 MCP 的工具调用链路和可观测性。

需要避免这样说：

> 我完整实现了官方 MCP 协议。

更稳妥的说法是：

> 当前版本使用官方 MCP Python SDK，通过 Streamable HTTP 暴露3个只读岗位工具，并复用现有 Tool Registry、SQL Guard 和工具日志。写操作工具、远程鉴权、Resources 与 Prompts 仍在后续范围内。

## 下一步优先级

1. 补充自动化测试，至少覆盖健康检查、岗位采集、技能抽取、Text2SQL Guard、简历解析和匹配分析。
2. 为公开写接口和远程 MCP 补充权限控制、限流与审计。
3. 让 Skill 定义真正约束允许工具、执行步骤和质量检查。
4. 整理 `eval/`，形成可复现的项目评估报告。
