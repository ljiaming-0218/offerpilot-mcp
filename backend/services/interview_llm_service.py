from typing import Any
import json

from backend.errors import AppError
from backend.services import llm_service


ALLOWED_QUESTION_TYPES = {
    "project_deep_dive",
    "requirement_gap",
    "rag_engineering",
    "agent_tool_calling",
    "text2sql_safety",
    "backend_design",
    "crawler_compliance",
    "deployment_ops",
    "motivation_pressure",
    "skill_foundation",
    "industry_specific",
}


def generate_interview_questions_by_llm(
    profile: dict[str, Any],
    job: dict[str, Any],
    job_skills: list[str],
    requirement: dict[str, Any],
    difficulty: str,
) -> list[dict[str, Any]]:
    system_prompt = """
你是 OfferPilot 的模拟面试官，面向中国互联网和 AI 应用开发、后端开发、Agent 工程、RAG、Text2SQL、数据库、安全、运维、前端、设计等实习岗位。

你的任务是根据给定岗位 JD、结构化岗位要求、候选人画像和常见面试考察方式，生成 3 道真实、具体、可追问的模拟面试题。

必须遵守：
1. 只能依据输入中的岗位信息、岗位要求、岗位技能和用户画像出题，不要编造公司内部信息。
2. 不要声称题目来自某个具体面经原文。
3. 如果岗位和用户画像明显不匹配，要优先问投递动机、能力迁移、短板补齐和风险解释。
4. 如果岗位是 AI/RAG/Agent/Text2SQL/后端/数据库相关，可以深入追问项目实现、原理、工程化、评测和排障。
5. 如果岗位不是 AI 后端方向，例如 UI、设计、运营、安全交付等，不要硬问 SQL Guard、Tool Registry 或 RAG。
6. 每道题都要包含出题原因、回答要点和出题依据。
7. 输出必须是严格 JSON，不要 Markdown，不要解释。

输出格式：
{
  "questions": [
    {
      "question_id": 1,
      "question_type": "project_deep_dive",
      "question": "问题正文",
      "why_ask": "为什么真实面试会问这个问题",
      "answer_points": ["回答要点1", "回答要点2", "回答要点3"],
      "related_evidence": ["岗位：...", "岗位要求：...", "用户项目：..."]
    }
  ]
}

question_type 只能从这些值中选择：
project_deep_dive, requirement_gap, rag_engineering, agent_tool_calling, text2sql_safety, backend_design, crawler_compliance, deployment_ops, motivation_pressure, skill_foundation, industry_specific
""".strip()

    user_prompt = json.dumps(
        {
            "difficulty": difficulty,
            "job": {
                "job_id": job.get("job_id"),
                "title": job.get("title"),
                "company_name": job.get("company_name"),
                "city": job.get("city"),
                "job_type": job.get("job_type"),
                "description": (job.get("description") or "")[:6000],
            },
            "job_skills": job_skills,
            "requirement": requirement,
            "user_profile": {
                "user_id": profile.get("user_id"),
                "education": profile.get("education"),
                "target_roles": profile.get("target_roles"),
                "target_cities": profile.get("target_cities"),
                "preferred_work_type": profile.get("preferred_work_type"),
                "skills": profile.get("skills"),
                "projects": profile.get("projects"),
                "weaknesses": profile.get("weaknesses"),
            },
        },
        ensure_ascii=False,
    )

    parsed = llm_service.chat_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        timeout=60,
    )
    return _normalize_questions(parsed)


def _normalize_questions(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    raw_questions = parsed.get("questions")
    if not isinstance(raw_questions, list):
        raise AppError(
            error="INTERVIEW_LLM_SCHEMA_INVALID",
            message="LLM 面试题结果缺少 questions 数组",
            status_code=502,
        )

    questions = []
    for index, item in enumerate(raw_questions[:3], start=1):
        if not isinstance(item, dict):
            continue

        question = _clean_text(item.get("question"))
        why_ask = _clean_text(item.get("why_ask"))
        answer_points = _clean_list(item.get("answer_points"))
        related_evidence = _clean_list(item.get("related_evidence"))
        question_type = _clean_text(item.get("question_type")) or "industry_specific"

        if question_type not in ALLOWED_QUESTION_TYPES:
            question_type = "industry_specific"

        if not question or not why_ask or len(answer_points) < 2:
            continue

        questions.append(
            {
                "question_id": index,
                "question_type": question_type,
                "question": question,
                "why_ask": why_ask,
                "answer_points": answer_points[:4],
                "related_evidence": related_evidence[:6],
            }
        )

    if len(questions) != 3:
        raise AppError(
            error="INTERVIEW_LLM_QUESTION_COUNT_INVALID",
            message="LLM 未生成 3 道合格面试题",
            status_code=502,
            generated_count=len(questions),
        )

    return questions


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for text in (_clean_text(item) for item in value) if text]
