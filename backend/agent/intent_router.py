import logging
import re
from pathlib import Path

import requests

from backend.errors import AppError
from backend.services import llm_service


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "agent_route_prompt.txt"
ALLOWED_SKILLS = {"job-search", "jd-crawl", "jd-analysis"}
MIN_ROUTE_CONFIDENCE = 0.55
logger = logging.getLogger("offerpilot.agent.router")


def route_task(task: str) -> dict:
    normalized_task = task.strip()
    if not normalized_task:
        raise AppError(
            error="AGENT_TASK_EMPTY",
            message="Agent 任务不能为空",
            status_code=400,
        )

    if llm_service.is_llm_available():
        try:
            result = llm_service.chat_json(
                system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
                user_prompt=f"用户任务：{normalized_task}",
                timeout=30,
            )
            routed = _normalize_llm_route(normalized_task, result)
            if routed is not None:
                return routed
            logger.warning("Agent LLM route was invalid; using rules fallback")
        except (AppError, requests.RequestException) as exc:
            logger.warning("Agent LLM routing failed; using rules fallback: %s", exc)

    return _route_task_by_rules(normalized_task)


def _normalize_llm_route(task: str, result: dict) -> dict | None:
    skill_name = str(result.get("skill_name", "")).strip()
    reason = str(result.get("reason", "")).strip()[:300]
    try:
        confidence = float(result.get("confidence", 0))
    except (TypeError, ValueError):
        return None

    if (
        skill_name not in ALLOWED_SKILLS
        or not reason
        or not MIN_ROUTE_CONFIDENCE <= confidence <= 1
    ):
        return None

    if skill_name == "jd-crawl" and _extract_url(task) is None:
        return None

    if skill_name == "jd-analysis" and _extract_job_id(task) is None:
        return None

    return {
        "task": task,
        "skill_name": skill_name,
        "reason": reason,
        "generation_mode": "llm",
        "confidence": round(confidence, 3),
    }


def _route_task_by_rules(task: str) -> dict:
    normalized_task = task.lower()

    if _extract_url(task) and _contains_any(normalized_task, ["采集", "抓取", "爬取", "岗位链接", "url", "招聘页面"]):
        return _rule_result(task, "jd-crawl", "任务包含公开 URL 和岗位采集意图")

    if _extract_job_id(task) and _contains_any(
        normalized_task,
        ["分析", "jd分析", "jd 分析", "提取技能", "技能标签", "岗位要求"],
    ):
        return _rule_result(task, "jd-analysis", "任务包含岗位 ID 和岗位分析意图")

    return _rule_result(task, "job-search", "规则兜底将任务作为已有岗位数据查询处理")


def _rule_result(task: str, skill_name: str, reason: str) -> dict:
    return {
        "task": task,
        "skill_name": skill_name,
        "reason": reason,
        "generation_mode": "rules_fallback",
        "confidence": 0.6,
    }


def _extract_url(task: str) -> str | None:
    match = re.search(r"https?://[^\s，。]+", task)
    return match.group(0) if match else None


def _extract_job_id(task: str) -> int | None:
    patterns = [
        r"(?:岗位|job)\s*(?:id\s*[=:：]?\s*)?(\d+)",
        r"(\d+)\s*号岗位",
        r"(?:分析|解析|提取)\s*(\d+)\s*(?:号)?(?:岗位)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, task, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
