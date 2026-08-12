import logging
import re
from pathlib import Path

import requests

from backend.errors import AppError
from backend.repositories import job_repository, skill_repository
from backend.services import llm_service


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "skill_extract_prompt.txt"
logger = logging.getLogger("offerpilot.skill_extract")

ALLOWED_IMPORTANCE = {"high", "medium", "low"}
ALLOWED_DIFFICULTY = {"high", "medium", "low"}
ALLOWED_CATEGORIES = {
    "RAG",
    "Agent",
    "MCP",
    "Tool Calling",
    "Text2SQL",
    "Prompt",
    "Backend",
    "Frontend",
    "Database",
    "Algorithm",
    "Deployment",
    "Evaluation",
    "Engineering",
    "LLM Basic",
}


SKILL_RULES = [
    {
        "skill_name": "RAG",
        "category": "RAG",
        "importance": "high",
        "keywords": ["RAG", "检索增强", "知识库", "向量检索"],
    },
    {
        "skill_name": "Agent",
        "category": "Agent",
        "importance": "high",
        "keywords": ["Agent", "智能体", "任务规划", "Agentic AI"],
    },
    {
        "skill_name": "MCP",
        "category": "MCP",
        "importance": "medium",
        "keywords": ["MCP", "Model Context Protocol"],
    },
    {
        "skill_name": "Tool Calling",
        "category": "Tool Calling",
        "importance": "high",
        "keywords": ["Tool Calling", "Function Calling", "函数调用", "工具调用"],
    },
    {
        "skill_name": "Text2SQL",
        "category": "Text2SQL",
        "importance": "high",
        "keywords": ["Text2SQL", "Text-to-SQL", "自然语言查询", "SQL生成"],
    },
    {
        "skill_name": "Python",
        "category": "Backend",
        "importance": "high",
        "keywords": ["Python"],
    },
    {
        "skill_name": "FastAPI",
        "category": "Backend",
        "importance": "medium",
        "keywords": ["FastAPI"],
    },
    {
        "skill_name": "MySQL",
        "category": "Database",
        "importance": "medium",
        "keywords": ["MySQL", "SQL"],
    },
    {
        "skill_name": "Prompt Engineering",
        "category": "Prompt",
        "importance": "medium",
        "keywords": ["Prompt", "提示词", "提示工程"],
    },
]

REQUIREMENT_RULES = {
    "education_requirements": [
        ("博士", ["博士"]),
        ("硕士", ["硕士", "研究生"]),
        ("本科及以上", ["本科及以上", "本科以上", "本科或以上"]),
        ("本科", ["本科"]),
        ("大专及以上", ["大专及以上", "专科及以上"]),
    ],
    "major_requirements": [
        ("计算机类", ["计算机", "软件工程", "网络工程"]),
        ("人工智能", ["人工智能", "机器学习", "深度学习"]),
        ("电子信息类", ["电子信息", "通信工程", "自动化"]),
        ("数学统计类", ["数学", "统计", "数据科学"]),
        ("软件工程", ["软件工程"]),
    ],
    "language_requirements": [
        ("英语四级", ["英语四级", "CET-4", "CET4", "四级"]),
        ("英语六级", ["英语六级", "CET-6", "CET6", "六级"]),
        ("英文文档阅读", ["英文文档", "英语读写", "英文读写", "英语能力"]),
    ],
    "experience_requirements": [
        ("实习经验", ["实习经验", "相关实习"]),
        ("项目经验", ["项目经验", "项目经历", "实践经验"]),
        ("竞赛经历", ["ACM", "竞赛", "比赛获奖"]),
        ("论文经历", ["论文", "顶会", "发表"]),
        ("开源贡献", ["开源", "开源社区"]),
    ],
    "soft_skill_requirements": [
        ("学习能力", ["学习能力", "快速学习"]),
        ("沟通能力", ["沟通能力", "表达能力"]),
        ("团队协作", ["团队协作", "团队合作"]),
        ("自驱力", ["自驱", "主动性", "责任意识"]),
        ("抗压能力", ["抗压"]),
    ],
    "bonus_requirements": [
        ("ACM/算法竞赛", ["ACM", "算法竞赛", "高水平竞赛"]),
        ("顶会论文", ["NeurIPS", "ICML", "AAAI", "顶级会议", "顶会"]),
        ("大厂实习", ["大厂实习", "知名企业实习"]),
        ("开源贡献", ["开源贡献", "开源社区贡献"]),
    ],
}


def extract_skills_for_job(job_id: int) -> dict:
    job = job_repository.get_job_by_id(job_id)

    if job is None:
        raise AppError(
            error="JOB_NOT_FOUND",
            message="岗位不存在",
            status_code=404,
        )

    text = f"{job.get('title', '')}\n{job.get('description', '')}"
    skills, requirement, generation_mode = _extract_job_requirements(text)

    if not skills and not _has_requirement(requirement):
        raise AppError(
            error="NO_REQUIREMENT_EXTRACTED",
            message="未从该岗位 JD 中识别到可用技能或岗位要求",
            status_code=422,
        )

    skill_repository.save_job_skills(job_id=job_id, skills=skills)

    job_repository.save_job_requirement(job_id=job_id, requirement=requirement)

    return {
        "job_id": job_id,
        "generation_mode": generation_mode,
        "skills": skills,
        "requirement": requirement,
        "job_orientation": requirement["job_orientation"],
        "difficulty": requirement["difficulty"],
        "summary": requirement["summary"],
    }


def _extract_job_requirements(text: str) -> tuple[list[dict], dict, str]:
    if llm_service.is_llm_available():
        try:
            result = llm_service.chat_json(
                system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
                user_prompt=f"岗位原文：\n{text}",
                timeout=60,
            )
            skills, requirement = _normalize_llm_result(result, text)
            if skills or _has_requirement(requirement):
                return skills, requirement, "llm"
            logger.warning("JD extraction returned no evidence-backed fields; using rules fallback")
        except (AppError, requests.RequestException) as exc:
            logger.warning("JD LLM extraction failed; using rules fallback: %s", exc)

    skills = _extract_skills_by_rules(text)
    return skills, _extract_requirement_by_rules(text, skills), "rules_fallback"


def _normalize_llm_result(result: dict, source_text: str) -> tuple[list[dict], dict]:
    skills = []
    seen_skills = set()
    for item in _as_dict_list(result.get("skills"))[:20]:
        name = _clean_text(item.get("skill_name"), 120)
        category = _clean_text(item.get("category"), 80)
        if category not in ALLOWED_CATEGORIES:
            category = "Engineering"
        importance = _clean_text(item.get("importance"), 20).lower()
        evidence = _verified_evidence(item.get("evidence"), source_text)
        key = name.lower()
        if not name or importance not in ALLOWED_IMPORTANCE or not evidence or key in seen_skills:
            continue
        seen_skills.add(key)
        skills.append(
            {
                "skill_name": name,
                "category": category,
                "importance": importance,
                "evidence": evidence,
            }
        )

    evidence_map = {}
    requirement = {"technical_skills": skills}
    for field in [
        "education_requirements",
        "major_requirements",
        "language_requirements",
        "experience_requirements",
        "soft_skill_requirements",
        "bonus_requirements",
        "responsibilities",
    ]:
        values, evidence = _normalize_evidence_items(result.get(field), source_text, limit=8 if field == "responsibilities" else 10)
        requirement[field] = values
        evidence_map[field] = evidence

    orientation = _clean_text(result.get("job_orientation"), 80) or _infer_job_orientation(skills, source_text)
    difficulty = _clean_text(result.get("difficulty"), 20).lower()
    if difficulty not in ALLOWED_DIFFICULTY:
        difficulty = _infer_difficulty(skills)
    summary = _clean_text(result.get("summary"), 300) or _build_summary(skills)

    requirement.update(
        {
            "evidence": evidence_map,
            "job_orientation": orientation,
            "difficulty": difficulty,
            "summary": summary,
        }
    )
    return skills, requirement


def _normalize_evidence_items(value, source_text: str, limit: int) -> tuple[list[str], list[dict]]:
    values = []
    evidence_items = []
    seen = set()
    for item in _as_dict_list(value):
        extracted_value = _clean_text(item.get("value"), 180)
        evidence = _verified_evidence(item.get("evidence"), source_text)
        key = extracted_value.lower()
        if not extracted_value or not evidence or key in seen:
            continue
        seen.add(key)
        values.append(extracted_value)
        evidence_items.append({"value": extracted_value, "evidence": evidence})
        if len(values) >= limit:
            break
    return values, evidence_items


def _verified_evidence(value, source_text: str) -> str | None:
    evidence = _clean_text(value, 240)
    if not evidence:
        return None
    normalized_source = _normalize_evidence_text(source_text)
    normalized_evidence = _normalize_evidence_text(evidence)
    return evidence if normalized_evidence and normalized_evidence in normalized_source else None


def _normalize_evidence_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _as_dict_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _clean_text(value, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:max_length]


def _extract_skills_by_rules(text: str) -> list[dict]:
    text_lower = text.lower()
    results = []

    for rule in SKILL_RULES:
        if any(keyword.lower() in text_lower for keyword in rule["keywords"]):
            results.append(
                {
                    "skill_name": rule["skill_name"],
                    "category": rule["category"],
                    "importance": rule["importance"],
                }
            )

    return results


def _extract_requirement_by_rules(text: str, skills: list[dict]) -> dict:
    requirement = {
        "technical_skills": skills,
        "education_requirements": [],
        "major_requirements": [],
        "language_requirements": [],
        "experience_requirements": [],
        "soft_skill_requirements": [],
        "bonus_requirements": [],
        "responsibilities": _extract_responsibilities(text),
        "job_orientation": _infer_job_orientation(skills, text),
        "difficulty": _infer_difficulty(skills),
        "summary": _build_summary(skills),
    }

    for field, rules in REQUIREMENT_RULES.items():
        requirement[field] = _match_rule_labels(text, rules)

    requirement["education_requirements"] = _dedupe_education(requirement["education_requirements"])

    return requirement


def _match_rule_labels(text: str, rules: list[tuple[str, list[str]]]) -> list[str]:
    result = []
    for label, keywords in rules:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            result.append(label)
    return result


def _extract_responsibilities(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    responsibilities = []
    in_responsibility_block = False

    for line in lines:
        if "岗位职责" in line or "职位介绍" in line or "工作内容" in line:
            in_responsibility_block = True
            continue
        if "岗位要求" in line or "任职要求" in line or "职位要求" in line:
            break
        if in_responsibility_block and _looks_like_responsibility_line(line):
            responsibilities.append(_clean_requirement_line(line))
        if len(responsibilities) >= 6:
            break

    return responsibilities


def _looks_like_responsibility_line(line: str) -> bool:
    action_words = ["参与", "负责", "协助", "开发", "设计", "优化", "构建", "打造", "跟踪", "落地", "实现"]
    has_action = any(word in line for word in action_words)
    has_list_marker = bool(re.match(r"^([0-9一二三四五六七八九十]+[、.．）)]|[-*])", line))
    return has_action and (has_list_marker or len(line) >= 18)


def _clean_requirement_line(line: str) -> str:
    return re.sub(r"^([0-9一二三四五六七八九十]+[、.．）)]|[-*])\s*", "", line).strip()[:180]


def _dedupe_education(items: list[str]) -> list[str]:
    if "本科及以上" in items and "本科" in items:
        items = [item for item in items if item != "本科"]
    if "硕士" in items and "本科" in items:
        items = [item for item in items if item != "本科"]
    return items


def _infer_job_orientation(skills: list[dict], text: str) -> str:
    skill_names = {skill["skill_name"] for skill in skills}

    if "Agent" in skill_names or "RAG" in skill_names or "大模型" in text:
        return "大模型应用 / AI 后端"

    if "Text2SQL" in skill_names:
        return "数据智能 / Text2SQL"

    if "FastAPI" in skill_names or "Python" in skill_names:
        return "后端开发 / AI 工程"

    return "技术岗位"


def _infer_difficulty(skills: list[dict]) -> str:
    high_count = sum(1 for skill in skills if skill["importance"] == "high")

    if high_count >= 3:
        return "high"

    if high_count >= 1:
        return "medium"

    return "low"


def _build_summary(skills: list[dict]) -> str:
    if not skills:
        return "该岗位未识别到明确技术技能，但已抽取其他岗位要求。"

    skill_names = [skill["skill_name"] for skill in skills]
    joined = "、".join(skill_names)
    return f"该岗位涉及 {joined}，可用于岗位匹配和面试追问。"


def _has_requirement(requirement: dict) -> bool:
    fields = [
        "education_requirements",
        "major_requirements",
        "language_requirements",
        "experience_requirements",
        "soft_skill_requirements",
        "bonus_requirements",
        "responsibilities",
    ]
    return any(requirement.get(field) for field in fields)
