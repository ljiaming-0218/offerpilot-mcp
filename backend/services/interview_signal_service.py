from typing import Any


SIGNAL_BANK = [
    {
        "name": "rag",
        "label": "RAG / 知识库应用",
        "keywords": ["rag", "检索增强", "知识库", "向量库", "embedding", "rerank", "召回", "chunk"],
        "question_type": "rag_engineering",
        "question": (
            "这个岗位涉及 RAG 或知识库能力。请结合你的项目说明：你会如何设计文档切分、向量检索、"
            "重排、引用返回和幻觉控制？如果召回结果不准，你会怎么定位问题？"
        ),
        "answer_points": [
            "说明数据从解析、切分、向量化、入库到检索的完整链路",
            "解释 chunk 大小、top_k、rerank、引用来源和答案约束如何影响效果",
            "补充评测方式，例如命中率、召回率、坏例分析和日志排查",
        ],
        "why_ask": "大模型应用岗位常把 RAG 作为落地能力考察点，面试官通常会追问召回质量、幻觉控制和评测方法。",
    },
    {
        "name": "agent",
        "label": "Agent / Tool Calling",
        "keywords": ["agent", "智能体", "tool", "工具调用", "function calling", "mcp", "trace", "memory"],
        "question_type": "agent_tool_calling",
        "question": (
            "这个岗位涉及 Agent 或工具调用。请说明你会如何设计 Tool Registry、工具输入输出、"
            "调用权限、失败处理和 Trace 记录，避免模型只是口头声称调用了工具。"
        ),
        "answer_points": [
            "说明 Agent Router、Skill、Tool Registry 和 Executor 的边界",
            "强调工具必须由后端真实执行，并记录 tool_call_logs 和 trace",
            "补充工具失败、参数错误、重复调用和高风险工具的处理策略",
        ],
        "why_ask": "Agent 工程化面试会重点考察工具调用是否真实、可控、可观测，而不是简单 Prompt 包装。",
    },
    {
        "name": "text2sql",
        "label": "Text2SQL / SQL 安全",
        "keywords": ["text2sql", "sql", "mysql", "数据库", "自然语言查询", "select", "join"],
        "question_type": "text2sql_safety",
        "question": (
            "这个岗位涉及数据库或自然语言查询。请结合你的 Text2SQL 设计说明：模型生成 SQL 后，"
            "你如何通过 SQL Guard 防止危险 SQL、字段幻觉和多语句执行？"
        ),
        "answer_points": [
            "说明生成 SQL 和执行 SQL 之间为什么要有安全校验层",
            "列出只允许 SELECT、禁止危险关键字、禁止多语句、自动 LIMIT 等规则",
            "说明 SQL 执行失败时如何返回错误、记录日志并避免暴露敏感信息",
        ],
        "why_ask": "Text2SQL 是 AI 后端岗位的高风险点，面试官会追问安全边界、数据库权限和错误处理。",
    },
    {
        "name": "backend",
        "label": "后端工程 / 数据建模",
        "keywords": ["fastapi", "springboot", "接口", "api", "后端", "服务", "repository", "事务", "日志"],
        "question_type": "backend_design",
        "question": (
            "如果让你把这个岗位的 JD 分析能力做成稳定后端服务，你会如何拆分 Router、Service、"
            "Repository，如何设计 MySQL 表结构和异常返回？"
        ),
        "answer_points": [
            "说明接口层、业务层、数据访问层各自负责什么",
            "结合 jobs、skills、job_skills、user_profiles、agent_traces 等表解释数据关系",
            "补充异常处理、日志、幂等、重复数据拦截和接口自查方法",
        ],
        "why_ask": "AI 应用开发不是只会调用模型，还要能把模型能力封装成稳定、可维护的后端系统。",
    },
    {
        "name": "crawler",
        "label": "公开数据采集 / 合规",
        "keywords": ["爬虫", "采集", "公开页面", "公开 url", "网页解析", "html", "source_url", "crawl"],
        "question_type": "crawler_compliance",
        "question": (
            "这个岗位需要处理真实公开岗位数据。请说明你的采集模块如何控制边界：哪些页面可以采集，"
            "哪些不能采集，失败和重复数据如何记录？"
        ),
        "answer_points": [
            "强调只采集无需登录、无验证码、公开可访问的岗位详情页",
            "说明 crawl_tasks、crawl_records 和 jobs 的职责区别",
            "说明请求超时、频率控制、失败原因、source_url 和原始文本摘要如何记录",
        ],
        "why_ask": "真实业务中的数据采集必须考虑合规、可追溯和失败排查，不能做无边界抓取。",
    },
    {
        "name": "deployment",
        "label": "部署 / 稳定性",
        "keywords": ["部署", "docker", "上线", "环境变量", "监控", "性能", "稳定", "生产"],
        "question_type": "deployment_ops",
        "question": (
            "如果这个项目要上线给面试官或真实用户演示，你会如何配置环境变量、数据库、"
            "服务启动、日志和健康检查？线上失败时你会先排查什么？"
        ),
        "answer_points": [
            "说明 API Key 和数据库密码只能放后端环境变量",
            "说明 MySQL、FastAPI、静态前端、健康检查和反向代理的部署关系",
            "补充线上排查顺序，例如 /health、应用日志、数据库连接、LLM 调用和网络请求",
        ],
        "why_ask": "AI 应用实习岗位常追问工程落地能力，部署和排障能区分 Demo 和可演示项目。",
    },
]


def build_interview_questions(
    profile: dict[str, Any],
    job: dict[str, Any],
    job_skills: list[str],
    requirement: dict[str, Any],
    difficulty: str,
) -> list[dict[str, Any]]:
    context = _build_context(profile, job, job_skills, requirement)
    signals = _rank_signals(context)
    profile_text = context["profile_text"]

    missing_skills = [
        skill for skill in job_skills
        if skill.lower() not in profile_text
    ]
    matched_skills = [
        skill for skill in job_skills
        if skill.lower() in profile_text
    ]

    selected = signals[:2] or [_fallback_signal()]
    questions = [
        _build_project_question(
            question_id=1,
            profile=profile,
            job=job,
            job_skills=job_skills,
            matched_skills=matched_skills,
            top_signal=selected[0] if selected else None,
        )
    ]

    for signal in selected:
        questions.append(
            _build_signal_question(
                question_id=len(questions) + 1,
                signal=signal,
                job=job,
                requirement=requirement,
                job_skills=job_skills,
            )
        )

    if len(questions) < 3:
        questions.append(
            _build_gap_question(
                question_id=len(questions) + 1,
                job=job,
                missing_skills=missing_skills,
                requirement_items=_requirement_items(requirement),
                difficulty=difficulty,
            )
        )

    return questions[:3]


def _build_context(
    profile: dict[str, Any],
    job: dict[str, Any],
    job_skills: list[str],
    requirement: dict[str, Any],
) -> dict[str, str]:
    job_parts = [
        job.get("title") or "",
        job.get("company_name") or "",
        job.get("job_type") or "",
        job.get("description") or "",
        " ".join(job_skills),
        " ".join(_requirement_items(requirement)),
        " ".join(requirement.get("responsibilities") or []),
    ]
    profile_parts = [
        profile.get("education") or "",
        profile.get("preferred_work_type") or "",
        " ".join(profile.get("target_roles") or []),
        " ".join(profile.get("target_cities") or []),
        " ".join(profile.get("skills") or []),
        " ".join(profile.get("projects") or []),
        " ".join(profile.get("weaknesses") or []),
    ]
    return {
        "job_text": "\n".join(job_parts).lower(),
        "profile_text": "\n".join(profile_parts).lower(),
    }


def _rank_signals(context: dict[str, str]) -> list[dict[str, Any]]:
    text = context["job_text"]
    scored = []
    for signal in SIGNAL_BANK:
        hits = sum(1 for keyword in signal["keywords"] if keyword.lower() in text)
        if hits:
            scored.append({**signal, "score": hits})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def _fallback_signal() -> dict[str, Any]:
    return next(signal for signal in SIGNAL_BANK if signal["name"] == "backend")


def _build_project_question(
    question_id: int,
    profile: dict[str, Any],
    job: dict[str, Any],
    job_skills: list[str],
    matched_skills: list[str],
    top_signal: dict[str, Any] | None,
) -> dict[str, Any]:
    project = _first(profile.get("projects")) or "你当前项目"
    focus = matched_skills[:3] or job_skills[:3] or ([top_signal["label"]] if top_signal else ["岗位核心要求"])

    return {
        "question_id": question_id,
        "question_type": "project_deep_dive",
        "question": (
            f"结合你的项目「{project}」，说明它和「{job['title']}」岗位里的 "
            f"{', '.join(focus)} 有什么对应关系？如果面试官继续追问实现细节，你会重点讲哪一段？"
        ),
        "why_ask": "真实实习面试通常先验证项目真实性，再追问项目是否覆盖岗位 JD 的核心要求。",
        "answer_points": [
            "先说明项目背景、你的职责和业务目标",
            "讲清楚你真正实现的模块、接口、数据流和技术取舍",
            "补充可验证结果，例如日志、Trace、数据库记录、评测样例或失败处理",
        ],
        "related_evidence": _compact([
            f"岗位：{job['title']}",
            f"公司：{job.get('company_name')}",
            f"岗位技能：{', '.join(job_skills[:6])}" if job_skills else "",
            f"命中考点：{top_signal['label']}" if top_signal else "",
            f"用户项目：{project}",
        ]),
    }


def _build_signal_question(
    question_id: int,
    signal: dict[str, Any],
    job: dict[str, Any],
    requirement: dict[str, Any],
    job_skills: list[str],
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question_type": signal["question_type"],
        "question": signal["question"],
        "why_ask": signal["why_ask"],
        "answer_points": signal["answer_points"],
        "related_evidence": _compact([
            f"岗位：{job['title']}",
            f"命中考点：{signal['label']}",
            f"岗位技能：{', '.join(job_skills[:6])}" if job_skills else "",
            f"岗位职责：{'; '.join((requirement.get('responsibilities') or [])[:2])}",
        ]),
    }


def _build_gap_question(
    question_id: int,
    job: dict[str, Any],
    missing_skills: list[str],
    requirement_items: list[str],
    difficulty: str,
) -> dict[str, Any]:
    if missing_skills:
        question = (
            f"这个岗位涉及 {', '.join(missing_skills[:4])}，你的画像里暂时没有明显体现。"
            "如果面试官问你这部分经验不足，你会如何解释，并证明自己能快速补上？"
        )
        evidence = f"缺失技能：{', '.join(missing_skills[:5])}"
    elif requirement_items:
        question = (
            f"岗位要求中提到 {', '.join(requirement_items[:4])}。"
            "请你逐条说明自己满足到什么程度，哪些内容还需要补充证据。"
        )
        evidence = f"岗位要求：{', '.join(requirement_items[:5])}"
    else:
        question = f"请按 {difficulty} 难度复盘你和这个岗位的匹配度，说明最有把握和最需要补强的部分。"
        evidence = "岗位要求结构化信息不足，需要结合 JD 原文回答"

    return {
        "question_id": question_id,
        "question_type": "requirement_gap",
        "question": question,
        "why_ask": "招聘 JD 会把技能、学历、语言、工程经验写成筛选条件，面试官常用追问确认候选人的短板和补救能力。",
        "answer_points": [
            "承认当前掌握程度，不要把未做过的内容说成已落地",
            "说明相近经验如何迁移到岗位要求",
            "给出明确补齐路径和时间安排",
        ],
        "related_evidence": _compact([
            f"岗位：{job['title']}",
            evidence,
        ]),
    }


def _requirement_items(requirement: dict[str, Any]) -> list[str]:
    fields = [
        "education_requirements",
        "major_requirements",
        "language_requirements",
        "experience_requirements",
        "soft_skill_requirements",
        "bonus_requirements",
    ]
    items = []
    for field in fields:
        items.extend(requirement.get(field) or [])
    return _unique(items)


def _first(values: list[str] | None) -> str | None:
    return values[0] if values else None


def _compact(values: list[str]) -> list[str]:
    return [value for value in values if value]


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        item = value.strip()
        key = item.lower()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result
