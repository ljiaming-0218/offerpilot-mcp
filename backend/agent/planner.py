import json
import logging
from pathlib import Path

import requests

from backend.errors import AppError
from backend.services import llm_service


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "agent_plan_prompt.txt"
MAX_PLAN_STEPS = 3
MIN_PLAN_CONFIDENCE = 0.55
logger = logging.getLogger("offerpilot.agent.planner")


def create_plan(task: str, skill_name: str, allowed_tools: set[str]) -> dict:
    if llm_service.is_llm_available():
        try:
            result = llm_service.chat_json(
                system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
                user_prompt=json.dumps(
                    {
                        "task": task,
                        "skill_name": skill_name,
                        "allowed_tools": sorted(allowed_tools),
                    },
                    ensure_ascii=False,
                ),
                timeout=30,
            )
            plan = _normalize_llm_plan(task, skill_name, allowed_tools, result)
            if plan is not None:
                return plan
            logger.warning("Agent LLM plan was invalid; using rules fallback")
        except (AppError, requests.RequestException) as exc:
            logger.warning("Agent LLM planning failed; using rules fallback: %s", exc)

    return _create_rules_plan(task, skill_name, allowed_tools)


def _normalize_llm_plan(
    task: str,
    skill_name: str,
    allowed_tools: set[str],
    result: dict,
) -> dict | None:
    reason = str(result.get("reason", "")).strip()[:300]
    try:
        confidence = float(result.get("confidence", 0))
    except (TypeError, ValueError):
        return None

    raw_steps = result.get("steps")
    if (
        not reason
        or not MIN_PLAN_CONFIDENCE <= confidence <= 1
        or not isinstance(raw_steps, list)
        or not 1 <= len(raw_steps) <= MAX_PLAN_STEPS
    ):
        return None

    steps = []
    seen_tools = set()
    for raw_step in raw_steps:
        if not isinstance(raw_step, dict):
            return None
        tool_name = str(raw_step.get("tool_name", "")).strip()
        step_reason = str(raw_step.get("reason", "")).strip()[:300]
        if tool_name not in allowed_tools or tool_name in seen_tools or not step_reason:
            return None
        seen_tools.add(tool_name)
        steps.append({"tool_name": tool_name, "reason": step_reason})

    if not _is_valid_plan_shape(task, skill_name, steps):
        return None

    return {
        "generation_mode": "llm",
        "reason": reason,
        "confidence": round(confidence, 3),
        "steps": steps,
    }


def _create_rules_plan(task: str, skill_name: str, allowed_tools: set[str]) -> dict:
    if skill_name == "job-search":
        steps = [_step("text2sql_query", "使用安全 Text2SQL 查询已有岗位数据")]
    elif skill_name == "jd-analysis":
        steps = [_step("extract_skills", "分析指定岗位并提取结构化要求")]
    elif skill_name == "jd-crawl":
        steps = [_step("crawl_job_url", "采集公开岗位页面并保存岗位")]
        if _requires_analysis(task):
            steps.append(_step("extract_skills", "使用采集结果中的岗位 ID 提取岗位要求"))
    elif skill_name == "profile-match":
        steps = [_step("match_my_profile", "使用当前登录用户画像匹配真实岗位")]
    elif skill_name == "mock-interview":
        steps = [_step("generate_my_mock_interview", "基于当前画像和指定岗位生成面试题")]
    elif skill_name == "answer-evaluator":
        steps = [_step("evaluate_my_interview_answer", "评估当前用户自己的面试回答")]
    elif skill_name == "study-plan":
        steps = [_step("generate_my_study_plan", "根据当前画像和岗位能力缺口生成学习优先级")]
    else:
        raise AppError(
            error="SKILL_NOT_SUPPORTED",
            message="当前 Planner 不支持该 Skill",
            status_code=400,
            skill_name=skill_name,
        )

    if any(step["tool_name"] not in allowed_tools for step in steps):
        raise AppError(
            error="PLAN_TOOL_NOT_ALLOWED",
            message="规划所需工具未被当前 Skill 授权",
            status_code=500,
            skill_name=skill_name,
            required_tools=[step["tool_name"] for step in steps],
            allowed_tools=sorted(allowed_tools),
        )

    return {
        "generation_mode": "rules_fallback",
        "reason": "根据 Skill 的确定性执行规则生成计划",
        "confidence": 0.8,
        "steps": steps,
    }


def _is_valid_plan_shape(task: str, skill_name: str, steps: list[dict]) -> bool:
    tool_names = [step["tool_name"] for step in steps]
    if skill_name == "job-search":
        return tool_names == ["text2sql_query"]
    if skill_name == "jd-analysis":
        return tool_names == ["extract_skills"]
    if skill_name == "jd-crawl":
        expected = ["crawl_job_url"]
        if _requires_analysis(task):
            expected.append("extract_skills")
        return tool_names == expected
    if skill_name == "profile-match":
        return tool_names == ["match_my_profile"]
    if skill_name == "mock-interview":
        return tool_names == ["generate_my_mock_interview"]
    if skill_name == "answer-evaluator":
        return tool_names == ["evaluate_my_interview_answer"]
    if skill_name == "study-plan":
        return tool_names == ["generate_my_study_plan"]
    return False


def _requires_analysis(task: str) -> bool:
    normalized = task.lower()
    return any(
        keyword in normalized
        for keyword in ["并分析", "分析岗位", "解析岗位", "提取技能", "岗位要求", "技能要求"]
    )


def _step(tool_name: str, reason: str) -> dict:
    return {"tool_name": tool_name, "reason": reason}
