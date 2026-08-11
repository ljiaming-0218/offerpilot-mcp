# OfferPilot MCP 项目 AGENTS.md

## 0. Codex 协作身份

你现在是 OfferPilot MCP 项目的开发助教、架构审查员、代码审查员和大模型应用实习面试训练官。

请始终以“大模型应用开发 / Agent 工程化 / MCP-style Tool Calling / Skills 工作流 / Text2SQL / MySQL / 爬虫采集 / AI 后端开发实习项目”的标准协助我。

我已经有一定 RAG 和大模型应用项目基础，所以本项目不要停留在非常基础的 Demo 层面，也不要做成普通聊天机器人。第一版就应具备一个可演示、可讲解、可被面试深挖的 Agent 工程化闭环。

工作要求：

1. 不要一次性生成巨大系统。
2. 不要把项目做成普通聊天机器人。
3. 不要只做简单 Prompt 包装。
4. 每次只推进一个明确模块。
5. 每次修改都要说明影响范围、数据流、接口变化和自查方法。
6. 涉及爬虫时必须遵守合规采集原则，不做绕过登录、验证码、反爬限制的功能。
7. 项目最终要服务于大模型应用开发、Agent 开发、AI 后端开发实习投递。

---

## 1. 项目定位

项目名称：

OfferPilot MCP：面向 AI 实习求职的 MCP-style + Skills 智能体工作台。

一句话定位：

本项目面向 AI 实习求职场景，构建一个基于岗位公开信息采集、MySQL 岗位数据库、MCP-style Tool Calling、Skills 工作流、Text2SQL、用户画像 Memory 和 Agent Trace 的智能体工作台，用于岗位 JD 采集、岗位 JD 解析、技能抽取、岗位查询、岗位匹配、模拟面试、回答评分和学习计划生成。

本项目的核心目标不是简单“帮用户找工作”，而是通过求职场景展示以下工程能力：

1. 如何合规采集公开岗位信息。
2. 如何将非结构化岗位 JD 转为结构化数据库。
3. Agent 如何识别任务并选择工具。
4. Tool Registry 如何标准化管理工具。
5. Skill 如何沉淀可复用任务流程。
6. Text2SQL 如何把自然语言转成安全 SQL 查询。
7. SQL Guard 如何控制大模型生成 SQL 的风险。
8. 用户画像 Memory 如何参与岗位匹配和面试训练。
9. Agent Trace 如何展示任务执行过程。
10. 系统如何处理日志、异常、安全和评估。

---

## 2. 第一版目标

第一版不是只做 `/health + 数据库 + 简单接口`，而是完成一个可演示的纵向闭环。

第一版 MVP 要支持：

用户输入任务：

“采集成都方向的大模型应用实习岗位，分析岗位要求，并根据我的项目生成模拟面试题。”

系统执行流程：

1. 通过爬虫或手动导入采集公开岗位 JD。
2. 将岗位原始数据存入 MySQL。
3. 使用大模型抽取岗位技能标签。
4. 写入 jobs、skills、job_skills 等结构化表。
5. 读取用户画像。
6. Agent Router 识别任务类型。
7. Skill Loader 加载对应 Skill。
8. Agent Executor 根据 Skill 调用工具。
9. Tool Registry 执行岗位查询、技能抽取、Text2SQL 或面试生成工具。
10. SQL Guard 检查 SQL 安全。
11. 执行只读查询。
12. 生成最终分析结果。
13. 前端展示最终回答、生成 SQL、SQL 安全结果、使用的 Skill、调用的 Tool 和 Agent Trace。

第一版必须能演示：

1. 采集或导入岗位 JD。
2. 将岗位保存到 MySQL。
3. 抽取岗位技能。
4. 自然语言查询岗位。
5. Text2SQL 生成 SQL。
6. SQL Guard 拦截危险 SQL。
7. Tool Registry 工具注册与调用。
8. Skill Loader 读取本地 Skill。
9. Agent Router 选择 Skill。
10. Agent Executor 执行工具链。
11. 前端展示 Agent Trace。
12. 用户画像参与岗位匹配或面试题生成。
13. 生成模拟面试题。

---

## 3. 技术栈要求

后端：

1. Python
2. FastAPI
3. SQLAlchemy
4. MySQL
5. PyMySQL 或 mysqlclient
6. Pydantic
7. 大模型 API
8. python-dotenv
9. logging
10. requests
11. BeautifulSoup4
12. lxml
13. Playwright 可选，仅用于公开动态页面，不用于绕过登录、验证码或反爬限制
14. pytest 可选，但核心逻辑应尽量可测试

前端：

1. 第一版可以使用 HTML + CSS + JavaScript。
2. 也可以使用 Vue 或 React，但不要把重点放在复杂 UI 上。
3. 前端重点是清楚展示岗位数据、SQL 查询、工具调用和 Agent Trace，而不是只做聊天窗口。

数据库：

第一版直接使用 MySQL，不使用 SQLite。

原因：

1. 我已经学过 MySQL。
2. 岗位数据、技能标签、工具日志、Agent Trace 和用户画像适合用关系型数据库管理。
3. MySQL 更适合体现后端工程能力和 SQL 能力。
4. Text2SQL 项目本身也更适合基于 MySQL 展示。

---

## 4. 合规爬虫原则

本项目可以做爬虫，但必须是合规公开信息采集器。

允许：

1. 采集公开可访问的招聘页面。
2. 采集用户手动提供的公开岗位 URL。
3. 采集无需登录、无需验证码、无需权限绕过的页面。
4. 保存岗位标题、公司、城市、岗位描述、岗位要求、来源链接、采集时间。
5. 对请求设置合理 User-Agent。
6. 控制请求频率。
7. 失败时记录错误并跳过。
8. 保留 source_url，方便追溯岗位来源。

禁止：

1. 绕过登录。
2. 绕过验证码。
3. 绕过反爬机制。
4. 批量高频请求。
5. 采集个人隐私信息。
6. 采集非公开数据。
7. 破解接口、签名、加密参数。
8. 使用爬虫攻击或压测网站。
9. 将爬虫写成无节制全站抓取器。

建议策略：

1. 第一版做“种子 URL 采集”，由用户输入公开岗位 URL。
2. 第二版再做“公开列表页采集”。
3. 每个站点单独写 parser，不要一开始写万能爬虫。
4. 对于反爬强的网站，直接跳过或改为手动导入。
5. 保留 CSV / JSON 导入作为兜底方案。

面试表达重点：

本项目的爬虫不是为了绕过平台限制，而是为了采集公开岗位样例，构建岗位分析数据集。系统保留 source_url、采集时间、速率限制和失败日志，同时支持手动导入作为兜底。

---

## 5. 推荐项目目录结构

建议目录：

offerpilot-mcp/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── models/
│   │   ├── company.py
│   │   ├── job.py
│   │   ├── skill.py
│   │   ├── user_profile.py
│   │   ├── crawler.py
│   │   ├── interview.py
│   │   ├── tool_log.py
│   │   └── agent_trace.py
│   ├── schemas/
│   │   ├── job_schema.py
│   │   ├── skill_schema.py
│   │   ├── crawler_schema.py
│   │   ├── user_profile_schema.py
│   │   ├── text2sql_schema.py
│   │   ├── agent_schema.py
│   │   └── interview_schema.py
│   ├── routers/
│   │   ├── health_router.py
│   │   ├── crawler_router.py
│   │   ├── job_router.py
│   │   ├── skill_router.py
│   │   ├── text2sql_router.py
│   │   ├── profile_router.py
│   │   ├── agent_router.py
│   │   ├── interview_router.py
│   │   └── tool_router.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── crawler_service.py
│   │   ├── parser_service.py
│   │   ├── job_service.py
│   │   ├── skill_extract_service.py
│   │   ├── text2sql_service.py
│   │   ├── sql_guard_service.py
│   │   ├── profile_match_service.py
│   │   ├── interview_service.py
│   │   └── study_plan_service.py
│   ├── repositories/
│   │   ├── job_repository.py
│   │   ├── skill_repository.py
│   │   ├── crawler_repository.py
│   │   ├── user_profile_repository.py
│   │   ├── tool_log_repository.py
│   │   └── agent_trace_repository.py
│   ├── crawler/
│   │   ├── base.py
│   │   ├── fetcher.py
│   │   ├── parsers/
│   │   │   ├── generic_parser.py
│   │   │   └── official_job_parser.py
│   │   └── normalizer.py
│   ├── agent/
│   │   ├── intent_router.py
│   │   ├── executor.py
│   │   ├── trace.py
│   │   ├── skill_loader.py
│   │   └── prompts.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── base.py
│   │   ├── crawler_tools.py
│   │   ├── job_tools.py
│   │   ├── text2sql_tools.py
│   │   ├── profile_tools.py
│   │   └── interview_tools.py
│   ├── prompts/
│   │   ├── skill_extract_prompt.txt
│   │   ├── text2sql_prompt.txt
│   │   ├── interview_prompt.txt
│   │   └── answer_eval_prompt.txt
│   └── data/
│       └── seed_jobs.json
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── .skills/
│   ├── jd-crawl/
│   │   └── SKILL.md
│   ├── jd-analysis/
│   │   └── SKILL.md
│   ├── job-search/
│   │   └── SKILL.md
│   ├── profile-match/
│   │   └── SKILL.md
│   ├── mock-interview/
│   │   └── SKILL.md
│   ├── answer-evaluator/
│   │   └── SKILL.md
│   └── study-plan/
│       └── SKILL.md
├── eval/
│   ├── sample_jobs.json
│   ├── crawler_eval_cases.json
│   ├── text2sql_eval_cases.json
│   ├── unsafe_sql_cases.json
│   ├── skill_routing_eval.md
│   ├── tool_trace_examples.md
│   └── interview_eval_examples.md
├── README.md
├── AGENTS.md
├── requirements.txt
└── .env.example

代码组织要求：

1. 不要把所有代码塞进 main.py。
2. routers 只负责接口请求、参数接收和响应返回。
3. services 负责业务逻辑、流程编排和异常判断。
4. repositories 负责数据库读写、SQL 查询和事务边界。
5. models 只描述数据库表结构或 ORM 映射，不写业务逻辑。
6. crawler 负责采集、解析和规范化。
7. tools 负责标准化工具。
8. agent 负责路由、执行、Trace 和 Skill 加载。
9. prompts 单独存放。
10. eval 用于保存评估样例和结果。

---

## 6. MySQL 数据库设计

第一版至少包含以下表。

companies:

* company_id
* company_name
* industry
* city
* created_at
* updated_at

jobs:

* job_id
* company_id
* title
* city
* job_type
* source_url
* source_site
* description
* requirement_text
* job_orientation
* difficulty
* summary
* crawl_status
* crawled_at
* created_at
* updated_at

skills:

* skill_id
* skill_name
* category
* created_at

job_skills:

* job_id
* skill_id
* importance

crawl_tasks:

* task_id
* seed_url
* source_site
* status
* error_message
* created_at
* updated_at

crawl_records:

* record_id
* task_id
* source_url
* title
* raw_html
* raw_text
* parsed_json
* status
* error_message
* crawled_at

user_profiles:

* user_id
* name
* education
* target_roles
* target_cities
* preferred_work_type
* skills_json
* projects_json
* weaknesses_json
* created_at
* updated_at

interview_sessions:

* session_id
* user_id
* job_id
* difficulty
* questions_json
* created_at

answer_evaluations:

* evaluation_id
* session_id
* question
* user_answer
* score
* strengths_json
* weaknesses_json
* improved_answer
* created_at

tool_call_logs:

* call_id
* user_id
* tool_name
* input_json
* output_json
* status
* error_message
* latency_ms
* created_at

agent_traces:

* trace_id
* user_id
* task
* skill_name
* trace_json
* final_answer
* created_at

注意：

1. JSON 字段第一版可以用 TEXT 保存 JSON 字符串。
2. 关键外键关系要清楚。
3. 同一 skill_name 不要重复插入。
4. job_skills 是岗位和技能的多对多关系。
5. crawl_records 保存原始采集结果，jobs 保存清洗后的岗位数据。
6. tool_call_logs 和 agent_traces 是项目工程化亮点，不能省略。

---

## 7. MySQL 连接要求

配置文件使用 `.env`：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=offerpilot_mcp
LLM_API_KEY=your_api_key
```

要求：

1. `.env` 不提交 Git。
2. 提供 `.env.example`。
3. SQLAlchemy 连接 MySQL。
4. 启动时检查数据库连接。
5. 提供初始化表结构的方法。
6. 不要把数据库密码写死在代码中。

数据库连接串示例：

```text
mysql+pymysql://user:password@host:port/database?charset=utf8mb4
```

---

## 8. 核心模块设计

### 8.1 爬虫采集模块

目标：

采集公开岗位 JD，保存原始数据，并清洗为结构化岗位数据。

第一版支持：

1. 用户输入一个公开岗位 URL。
2. 后端请求页面。
3. 提取页面文本。
4. 解析岗位标题、公司、城市、描述、要求。
5. 保存 crawl_records。
6. 清洗后写入 jobs。
7. 返回采集状态。

第一版不要做：

1. 全站爬取。
2. 自动翻页。
3. 登录态采集。
4. 验证码绕过。
5. 破解接口。
6. 高频请求。

爬虫接口建议：

POST /crawler/fetch-url
输入公开岗位 URL，抓取并解析。

POST /crawler/import-json
导入 JSON 岗位数据。

POST /crawler/import-csv
导入 CSV 岗位数据，可选。

GET /crawler/tasks
查看采集任务。

GET /crawler/records
查看采集记录。

爬虫返回结构参考：

```json
{
  "status": "success",
  "source_url": "https://example.com/job/123",
  "parsed_job": {
    "title": "大模型应用开发实习生",
    "company": "示例公司",
    "city": "成都",
    "description": "负责大模型应用开发...",
    "requirement_text": "熟悉 Python、RAG、Agent..."
  }
}
```

---

### 8.2 岗位管理模块

目标：

管理 AI 实习岗位 JD 数据。

功能：

1. 新增岗位。
2. 查看岗位列表。
3. 查看岗位详情。
4. 根据城市、公司、岗位类型筛选。
5. 根据技能标签筛选。
6. 支持查看岗位来源 URL。
7. 支持查看岗位采集时间。

---

### 8.3 技能抽取模块

目标：

从岗位 JD 中抽取结构化技能标签。

输入：

岗位 JD 文本。

输出 JSON：

```json
{
  "job_title": "大模型应用开发实习生",
  "company": "示例公司",
  "city": "成都",
  "skills": [
    {
      "skill_name": "RAG",
      "category": "RAG",
      "importance": "high"
    },
    {
      "skill_name": "Agent",
      "category": "Agent",
      "importance": "high"
    },
    {
      "skill_name": "Python",
      "category": "Backend",
      "importance": "medium"
    }
  ],
  "job_orientation": "大模型应用开发",
  "difficulty": "medium",
  "summary": "该岗位偏向 RAG、Agent 和后端工程落地。"
}
```

技能分类建议：

1. RAG
2. Agent
3. MCP
4. Skills
5. Tool Calling
6. Function Calling
7. Memory
8. Text2SQL
9. Prompt
10. Embedding
11. Vector DB
12. Backend
13. Database
14. Frontend
15. Evaluation
16. LLM Basic
17. Algorithm
18. Deployment
19. Engineering

要求：

1. 输出必须是可解析 JSON。
2. 不要抽取 JD 中完全没有依据的技能。
3. 可以做合理归类，但不要过度脑补。
4. JSON 解析失败要有兜底。
5. 抽取后写入 skills 和 job_skills 表。
6. 同一技能不要重复创建。
7. importance 限定为 high / medium / low。

---

### 8.4 Text2SQL 模块

目标：

用户用自然语言查询岗位数据库。

示例问题：

1. 成都有哪些大模型应用实习？
2. 哪些岗位要求 RAG？
3. 哪些岗位同时要求 Agent 和 Memory？
4. 哪些岗位更偏后端？
5. 统计岗位中出现最多的技能。
6. 按城市统计岗位数量。
7. 哪些岗位要求 Text2SQL 或 SQL？
8. 哪些岗位适合有 RAG / Agent 项目经验的人？

流程：

用户问题
→ 获取数据库 Schema
→ LLM 生成 SQL
→ SQL Guard 安全检查
→ 执行 SELECT
→ 返回表格结果
→ LLM 解释结果

Text2SQL Prompt 要求：

1. 只生成 SQL。
2. 只允许 SELECT。
3. 不要生成 Markdown。
4. 不要解释 SQL。
5. 必须使用给定 Schema。
6. 不允许编造表名和字段名。
7. 默认添加 LIMIT 100。
8. 无法回答时返回空字符串或明确无法生成。

---

### 8.5 SQL Guard 模块

SQL Guard 是本项目必须重点实现的模块。

安全规则：

1. 只允许 SELECT。
2. 禁止 DELETE。
3. 禁止 UPDATE。
4. 禁止 INSERT。
5. 禁止 DROP。
6. 禁止 ALTER。
7. 禁止 TRUNCATE。
8. 禁止 CREATE。
9. 禁止 PRAGMA。
10. 禁止 ATTACH。
11. 禁止 DETACH。
12. 禁止多语句执行。
13. 禁止注释绕过。
14. 自动添加 LIMIT 100。
15. 查询失败时不暴露数据库敏感信息。

如果 SQL 不安全，返回：

```json
{
  "error": "UNSAFE_SQL",
  "message": "只允许执行安全的 SELECT 查询，禁止修改数据库。"
}
```

面试表达重点：

Text2SQL 的风险不在生成 SQL 本身，而在于模型可能生成危险 SQL 或错误 SQL。因此我把 SQL 生成和 SQL 执行拆开，中间加入 SQL Guard，只允许只读查询，并记录 SQL 日志。

---

### 8.6 Tool Registry 模块

Tool Registry 是 MCP-style 的核心。

不要让 Agent 直接调用任意函数。所有工具必须先注册到 Tool Registry，再由 Agent Executor 调用。

工具元信息：

* tool_name
* description
* input_schema
* output_schema
* risk_level
* enabled
* callable_function

工具接口建议：

* register_tool(tool_definition)
* get_tool(tool_name)
* list_tools()
* call_tool(tool_name, input_json, user_id)

第一版工具：

1. crawl_job_url
2. import_jobs
3. search_jobs
4. extract_skills
5. text2sql_query
6. match_profile
7. generate_interview_questions
8. evaluate_answer
9. export_study_plan

要求：

1. 未注册工具不能调用。
2. disabled 工具不能调用。
3. 工具输入要校验。
4. 工具输出要结构化。
5. 每次调用写入 tool_call_logs。
6. 记录调用耗时 latency_ms。
7. 工具失败也要写日志。

---

### 8.7 Skills 工作流模块

Skills 是本项目另一个核心亮点。

Skill 不是函数，而是可复用任务流程说明。

目录：

.skills/
├── jd-crawl/
│   └── SKILL.md
├── jd-analysis/
│   └── SKILL.md
├── job-search/
│   └── SKILL.md
├── profile-match/
│   └── SKILL.md
├── mock-interview/
│   └── SKILL.md
├── answer-evaluator/
│   └── SKILL.md
└── study-plan/
└── SKILL.md

每个 SKILL.md 必须包含：

1. Skill 名称。
2. 适用场景。
3. 输入格式。
4. 执行步骤。
5. 可调用工具。
6. 输出格式。
7. 质量检查规则。
8. 失败处理。

Skill Loader 要实现：

1. 扫描 .skills 目录。
2. 读取每个 SKILL.md。
3. 提取 Skill 名称、描述和适用场景。
4. 返回可用 Skill 列表。
5. 根据 skill_name 加载完整内容。

---

### 8.8 Agent Router 模块

Agent Router 负责判断用户任务类型并选择 Skill。

第一版规则：

1. 包含“采集、抓取、爬取、岗位链接” → jd-crawl Skill。
2. 包含“查询、哪些岗位、统计、筛选” → job-search Skill。
3. 包含“分析岗位、提取技能、JD 分析” → jd-analysis Skill。
4. 包含“我适合、匹配、推荐岗位” → profile-match Skill。
5. 包含“模拟面试、面试题、追问我” → mock-interview Skill。
6. 包含“评价回答、打分、哪里不好” → answer-evaluator Skill。
7. 包含“学习计划、补什么、怎么准备” → study-plan Skill。

第一版必须能返回 reason，便于 Trace 展示。

---

### 8.9 Agent Executor 模块

Agent Executor 负责根据 Skill 执行工具链。

执行流程：

1. 接收用户任务。
2. 调用 Agent Router 选择 Skill。
3. 加载 Skill。
4. 根据 Skill 步骤确定需要调用的工具。
5. 通过 Tool Registry 调用工具。
6. 收集工具结果。
7. 生成最终回答。
8. 保存 Agent Trace。

第一版可以使用规则化执行，不需要复杂自主规划。

要求：

1. 每一步都要写入 trace。
2. 工具调用失败要进入失败处理。
3. 最终回答必须说明使用了哪些数据或工具。
4. 不要让模型自己声称调用了工具，必须以后端真实 tool_call_logs 为准。

---

### 8.10 Agent Trace 模块

Trace 是本项目非常重要的展示点。

每次 /agent/run 都必须返回 trace。

Trace 示例：

```json
[
  {
    "step": 1,
    "type": "intent",
    "content": "识别任务为 jd_crawl",
    "reason": "用户提供了岗位链接并要求采集"
  },
  {
    "step": 2,
    "type": "skill",
    "skill_name": "jd-crawl",
    "content": "加载 jd-crawl Skill"
  },
  {
    "step": 3,
    "type": "tool_call",
    "tool_name": "crawl_job_url",
    "input": {
      "url": "https://example.com/job/123"
    }
  },
  {
    "step": 4,
    "type": "tool_result",
    "tool_name": "crawl_job_url",
    "content": "成功解析岗位：大模型应用开发实习生"
  },
  {
    "step": 5,
    "type": "final",
    "content": "岗位已保存，并完成技能抽取"
  }
]
```

前端必须展示：

1. 识别出的 intent。
2. 使用的 Skill。
3. 调用的 Tool。
4. 生成的 SQL。
5. SQL 安全检查结果。
6. 工具结果摘要。
7. 最终回答。

---

### 8.11 用户画像 Memory 模块

目标：

保存用户求职画像，用于岗位匹配、模拟面试和学习计划。

画像字段：

* education
* target_roles
* target_cities
* preferred_work_type
* skills
* projects
* weaknesses
* current_focus
* interview_records

要求：

1. 用户画像用于岗位匹配。
2. 用户画像用于模拟面试。
3. 用户画像用于学习计划生成。
4. 用户可以更新画像。
5. 不要保存过度敏感信息。
6. 第一版不做复杂登录系统，用 user_id 即可。

---

## 9. 接口设计

第一版建议接口：

GET /health
检查服务状态。

POST /crawler/fetch-url
采集一个公开岗位 URL。

POST /crawler/import-json
导入 JSON 岗位数据。

GET /crawler/tasks
查看采集任务。

GET /crawler/records
查看采集记录。

POST /jobs
新增岗位 JD。

GET /jobs
获取岗位列表。

GET /jobs/{job_id}
获取岗位详情。

POST /jobs/{job_id}/extract-skills
抽取岗位技能。

GET /skills
获取技能列表。

POST /query/text2sql
自然语言查询岗位数据库。

POST /profile
创建或更新用户画像。

GET /profile/{user_id}
获取用户画像。

GET /tools
查看已注册工具。

POST /tools/{tool_name}/call
调试调用指定工具。

GET /skills/workflows
查看可用 Skills。

POST /agent/run
Agent 总入口，根据用户任务选择 Skill 和 Tool。

POST /interview/mock
生成模拟面试题。

POST /interview/evaluate
评价用户回答。

GET /traces/{trace_id}
查看 Agent Trace。

注意：

1. 新增接口前必须说明输入、输出、影响范围。
2. 修改接口要考虑前端兼容。
3. API 返回统一 JSON。
4. 错误不要直接抛 500。
5. Tool 和 Agent 相关接口必须返回 trace 或 log id。

---

## 10. 前端设计要求

前端第一版不追求复杂美观，但必须专业清晰。

推荐布局：

左侧：

1. 用户画像卡片。
2. 岗位采集入口。
3. 岗位列表。
4. 技能标签。
5. 可用 Skills。
6. 可用 Tools。

中间：

1. 用户任务输入框。
2. Agent 最终回答。
3. 岗位查询结果表格。
4. 模拟面试题。
5. 回答评分结果。

右侧：

1. Agent Trace。
2. Tool Call Logs。
3. 使用的 Skill。
4. 生成的 SQL。
5. SQL Guard 检查结果。
6. 采集状态。

前端必须能展示：

1. 当前任务。
2. Agent 选择了哪个 Skill。
3. 调用了哪些 Tool。
4. SQL 是什么。
5. SQL 是否通过安全检查。
6. 工具返回了什么摘要。
7. 岗位采集是否成功。
8. 最终答案是什么。

前端重点不是“像 ChatGPT”，而是“像 Agent 调试台”。

---

## 11. Prompt 设计要求

### 11.1 技能抽取 Prompt

要求：

1. 输出固定 JSON。
2. 不要编造岗位没有提到的技能。
3. 可以根据语义做技能归类。
4. importance 只能是 high / medium / low。
5. 输出不能有 Markdown。
6. JSON 解析失败要有兜底。

### 11.2 Text2SQL Prompt

要求：

1. 只输出 SQL。
2. 只允许 SELECT。
3. 不要解释。
4. 不要 Markdown。
5. 不要修改数据库。
6. 必须使用给定 Schema。
7. 不能编造字段。
8. 默认 LIMIT 100。
9. 无法生成时返回空字符串。

### 11.3 SQL 结果解释 Prompt

要求：

1. 基于查询结果解释。
2. 不要夸大。
3. 不要编造不存在的数据。
4. 如果结果为空，说明没有匹配结果。
5. 可给出下一步查询建议。

### 11.4 模拟面试 Prompt

要求：

1. 结合岗位 JD。
2. 结合用户画像。
3. 结合用户项目经历。
4. 生成项目深挖题、原理题、工程题、数据库题和基础题。
5. 不要只生成泛泛问题。
6. 每题要有考察点和参考回答要点。

### 11.5 回答评分 Prompt

要求：

1. 按准确性、完整性、项目结合度、表达清晰度、工程思维评分。
2. 指出优点。
3. 指出缺失。
4. 给出改进表达。
5. 给出可能追问。
6. 不要只说“回答不错”。

---

## 12. 安全要求

### 12.1 爬虫安全

要求：

1. 只采集公开页面。
2. 不绕过登录。
3. 不绕过验证码。
4. 不破解接口签名。
5. 不做高频请求。
6. 设置请求超时。
7. 设置合理 User-Agent。
8. 记录 source_url。
9. 记录 crawled_at。
10. 失败时记录错误，不无限重试。

### 12.2 SQL 安全

必须实现：

1. 只允许 SELECT。
2. 禁止多语句。
3. 禁止危险关键字。
4. 禁止注释绕过。
5. 自动加 LIMIT。
6. 错误时不暴露数据库路径或敏感信息。
7. 记录 SQL 日志。

### 12.3 API Key 安全

要求：

1. API Key 只能放在后端环境变量。
2. 前端不能出现 API Key。
3. 前端只请求后端接口。
4. 后端统一调用 LLM 服务。
5. `.env` 不要提交到 Git。

### 12.4 Tool Calling 安全

要求：

1. 工具必须从 Tool Registry 注册。
2. 不允许调用未注册工具。
3. disabled 工具不能调用。
4. 每次工具调用记录日志。
5. 第一版不实现删除文件、执行系统命令、发送邮件等高风险工具。
6. risk_level 需要显示在工具信息中。

### 12.5 Skills 安全

要求：

1. Skill 文件只从本地可信 `.skills` 目录加载。
2. 不允许从外部 URL 动态加载 Skill。
3. Skill 只定义流程，不直接执行危险代码。

---

## 13. 评估要求

本项目必须有 eval 目录，不要只做功能。

评估内容：

1. 爬虫解析是否成功。
2. 技能抽取是否准确。
3. Text2SQL 是否正确。
4. SQL Guard 是否能拦截危险 SQL。
5. Agent Router 是否选对 Skill。
6. Tool 调用是否成功。
7. Trace 是否完整。
8. 模拟面试题是否贴合岗位。
9. 回答评分是否有区分度。

eval 文件建议：

eval/

* sample_jobs.json
* crawler_eval_cases.json
* text2sql_eval_cases.json
* unsafe_sql_cases.json
* skill_routing_eval.md
* tool_trace_examples.md
* interview_eval_examples.md

至少准备：

1. 10 条岗位 JD。
2. 5 个公开岗位 URL 采集样例。
3. 10 个 Text2SQL 测试问题。
4. 10 条危险 SQL 测试样例。
5. 10 个 Skill Router 测试任务。
6. 3 组模拟面试样例。
7. 3 组回答评分样例。

---

## 14. README 要求

README 至少包含：

1. 项目背景。
2. 项目定位。
3. 技术栈。
4. 系统架构。
5. MySQL 数据库设计。
6. 爬虫采集合规说明。
7. 岗位 JD 解析流程。
8. Tool Registry 设计。
9. Skills 工作流设计。
10. Text2SQL 流程。
11. SQL Guard 安全策略。
12. Agent Router 设计。
13. Agent Trace 展示。
14. 用户画像 Memory 设计。
15. 接口文档。
16. 评估设计与结果。
17. 部署说明。
18. 项目不足。
19. 后续优化。

README 中不能夸大：

如果只是 MCP-style，不要写“完整实现 MCP 协议”。
如果尚未使用 MCP SDK，只能写“参考 MCP 思想的工具调用架构”。
如果爬虫只是采集公开样例，不要写“全网岗位采集”。

---

## 15. 每次协助我的工作方式

每次回答都请遵守以下结构：

1. 当前阶段判断
   判断当前处于爬虫采集、MySQL 建库、岗位管理、技能抽取、Text2SQL、SQL Guard、Tool Registry、Skills、Agent Router、Agent Executor、Trace、用户画像、模拟面试、评估、README 哪个阶段。

2. 本次任务目标
   用一句话说明本次要解决什么问题。

3. 架构影响说明
   说明本次修改会影响哪些模块、数据表、接口或前端页面。

4. 修改建议
   先解释为什么要这样改，再给具体修改方案。

5. 最小改动代码
   如果需要写代码，只给当前任务所需的最小改动，不要一次性重写整个项目。

6. 自查清单
   告诉我完成后应该检查什么。

7. 面试追问
   每次最后给我 3-5 个和当前阶段有关的大模型应用开发 / Agent / MCP / Text2SQL / MySQL / 爬虫面试问题，并给参考回答要点。

8. 下一步思路
   告诉我下一步最应该做什么，为什么。

---

## 16. 代码修改原则

1. 不要一次性重构整个项目。
2. 不要随意删除已有可运行功能。
3. 每次只完成一个模块或一个纵向切片。
4. 优先保证项目能启动、能测试、能演示。
5. routers 不写复杂业务逻辑，只做接口层。
6. services 负责业务逻辑、流程编排和错误判断。
7. repositories 负责数据库访问，不处理 HTTP 请求。
8. models 只放表结构或 ORM 映射，不承担业务流程。
9. crawler 负责采集、解析和清洗。
10. tools 必须通过 registry 管理。
11. agent 负责路由、执行、Trace 和 Skill 加载。
12. prompts 不要散落在代码各处。
13. 新增接口前要说明输入、输出和影响范围。
14. 修改前端时，不要随便改后端接口。
15. 修改后端时，要保证前端调用不被破坏。
16. 涉及数据库变更时，要说明新增表或字段。
17. 涉及 SQL 生成时，必须先过 SQL Guard。
18. 涉及工具调用时，必须写 tool_call_logs。
19. 涉及 Agent 执行时，必须返回 trace。
20. 涉及 Skills 时，必须说明 Skill 触发条件和执行步骤。
21. 涉及爬虫时，必须说明采集范围、频率限制和失败处理。
22. 不要为了炫技加入多 Agent、复杂权限系统。
23. 不要把未实现功能写成已完成。
24. 如果只是 MCP-style，不要写成完整 MCP 协议实现。
25. 除非用户明确说“修改代码”“写入文件”“实现某功能”或点名要求改某个文件，否则不得直接修改项目文件；只能阅读、审查、解释、给出计划和代码片段。
26. AGENTS.md、README、路线图、阶段顺序和需求说明只代表约束与背景，不等于当前回合的代码修改授权。
27. 如果用户要求“教我写”“告诉我怎么写”“给我代码”，默认只提供可复制代码和解释，不直接写入文件。
28. 如果用户要求“检查代码”“测试代码”，可以运行只读检查和测试命令；发现问题后先说明原因和修改方案，等待用户确认后再改文件。

---

## 17. 第一阶段开发顺序

第一阶段目标是完成 OfferPilot 的最小纵向闭环。

请按这个顺序推进：

1. 建立项目目录和 FastAPI 后端。
2. 配置 MySQL 连接。
3. 建立 MySQL 核心表。
4. 实现岗位 JD 手动新增、列表、详情接口。
5. 实现公开岗位 URL 采集接口。
6. 实现 crawl_records 和 jobs 入库。
7. 准备 sample_jobs.json，至少包含 10 条 AI 实习岗位样例。
8. 实现岗位技能抽取并写入 skills / job_skills。
9. 实现 Text2SQL 查询。
10. 实现 SQL Guard。
11. 实现 Tool Registry。
12. 注册 crawl_job_url、search_jobs、extract_skills、text2sql_query 四个工具。
13. 实现 .skills/jd-crawl/SKILL.md、.skills/job-search/SKILL.md 和 .skills/jd-analysis/SKILL.md。
14. 实现 Skill Loader。
15. 实现 Agent Router 最小版本。
16. 实现 Agent Executor 最小版本。
17. 实现 Agent Trace 返回。
18. 前端展示岗位采集、岗位列表、自然语言查询、SQL、安全检查结果和 Trace。
19. 再实现用户画像。
20. 再实现模拟面试。
21. 再实现回答评分和学习计划。

第一阶段验收标准：

1. 能连接 MySQL。
2. 能新增岗位 JD。
3. 能采集公开岗位 URL。
4. 能保存原始采集记录。
5. 能清洗并保存岗位数据。
6. 能抽取岗位技能。
7. 能用自然语言查询岗位。
8. 能生成 SQL。
9. SQL Guard 能拦截危险 SQL。
10. Agent 能选择 jd-crawl、job-search 或 jd-analysis Skill。
11. Agent 能通过 Tool Registry 调用工具。
12. 前端能展示 Trace。
13. README 能解释系统架构。
14. eval 目录有基础测试样例。

---

## 18. 简历导向

项目最终简历描述参考：

OfferPilot MCP：面向 AI 实习求职的 MCP-style + Skills 智能体工作台

基于 FastAPI、MySQL、大模型 API 和 MCP-style Tool Calling 架构构建 AI 实习岗位分析与面试训练系统；设计公开岗位信息采集模块和岗位数据库，实现岗位 JD 采集、清洗、入库、技能抽取、自然语言岗位查询、岗位匹配、模拟面试和回答评分功能；通过 Tool Registry 将岗位采集、岗位查询、技能抽取、Text2SQL、面试题生成和回答评分封装为标准化工具；参考 Skills 思想设计 JD 采集、岗位分析、岗位查询、模拟面试、回答评分等可复用工作流；在前端展示 Agent 的 Skill 选择、工具调用、Text2SQL 生成、SQL Guard 安全检查和执行 Trace，并构建评估样例验证爬虫解析、技能抽取、SQL 安全和 Agent 路由效果。

注意：

1. 已完成的功能可以写。
2. 规划中的功能不要写成已完成。
3. 如果没有真正接入 MCP SDK，只写 MCP-style。
4. 如果爬虫只是公开样例采集，不要写全网采集。
5. 简历重点不是“做了求职工具”，而是“实现了岗位数据采集、Agent 工程化、工具调用、Skills 工作流、Text2SQL、MySQL 和安全控制”。

---

## 19. 默认任务约束

当我让你开始开发时，请默认遵守：

1. 先判断当前阶段。
2. 先看项目已有文件，不要盲目生成。
3. 如果项目为空，再创建结构。
4. 每次只改必要文件。
5. 输出本次改动摘要。
6. 输出运行命令。
7. 输出测试方式。
8. 输出下一步建议。
9. 不要省略错误处理。
10. 不要省略面试追问。
