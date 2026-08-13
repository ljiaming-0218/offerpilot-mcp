import logging
from pathlib import Path

import requests

from backend.errors import AppError
from backend.repositories import text2sql_repository
from backend.services import llm_service, sql_guard_service


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "text2sql_prompt.txt"
logger = logging.getLogger("offerpilot.text2sql")


def query_jobs_by_question(question: str) -> dict:
    raw_sql, generation_mode = _generate_sql(question)
    guard_result = sql_guard_service.check_sql_safety(raw_sql)

    if not guard_result["safe"] and generation_mode == "llm":
        repaired_sql = _repair_sql(
            question=question,
            unsafe_sql=raw_sql,
            guard_reason=guard_result["reason"],
        )
        if repaired_sql:
            raw_sql = repaired_sql
            generation_mode = "llm_repaired"
            guard_result = sql_guard_service.check_sql_safety(raw_sql)

    if not guard_result["safe"]:
        raise AppError(
            error="UNSAFE_SQL",
            message="SQL 未通过安全检查",
            status_code=400,
            reason=guard_result["reason"],
            sql=guard_result["sql"],
        )

    rows = text2sql_repository.execute_readonly_sql(guard_result["sql"])

    return {
        "question": question,
        "sql": guard_result["sql"],
        "generation_mode": generation_mode,
        "safe": guard_result["safe"],
        "reason": guard_result["reason"],
        "rows": rows,
    }


def _generate_sql(question: str) -> tuple[str, str]:
    if llm_service.is_llm_available():
        try:
            result = llm_service.chat_json(
                system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
                user_prompt=f"用户问题：{question.strip()}",
            )
            sql = str(result.get("sql", "")).strip()
            if not sql:
                raise AppError(
                    error="LLM_SQL_EMPTY",
                    message="LLM 未返回 SQL",
                    status_code=502,
                )
            return sql, "llm"
        except (AppError, requests.RequestException) as exc:
            logger.warning("Text2SQL LLM generation failed; using rules fallback: %s", exc)
            return _generate_sql_by_rules(question), "rules_fallback"

    return _generate_sql_by_rules(question), "rules_fallback"


def _repair_sql(question: str, unsafe_sql: str, guard_reason: str) -> str | None:
    try:
        result = llm_service.chat_json(
            system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
            user_prompt=(
                f"用户问题：{question.strip()}\n"
                f"上一条 SQL：{unsafe_sql}\n"
                f"SQL Guard 拒绝原因：{guard_reason}\n"
                "请根据拒绝原因修正 SQL，仍然只输出 {\"sql\": \"SELECT ...\"}。"
            ),
        )
    except (AppError, requests.RequestException):
        return None

    sql = str(result.get("sql", "")).strip()
    return sql or None


def _generate_sql_by_rules(question: str) -> str:
    question = question.strip()

    if "按公司" in question and ("岗位数量" in question or "岗位数" in question):
        city = _extract_city(question)
        city_filter = f"WHERE j.city LIKE '%{city}%'" if city else ""
        limit = _extract_requested_limit(question, default=10)
        return f"""
        SELECT
            c.company_id,
            c.company_name,
            COUNT(j.job_id) AS job_count
        FROM companies c
        JOIN jobs j ON j.company_id = c.company_id
        {city_filter}
        GROUP BY c.company_id, c.company_name
        ORDER BY job_count DESC
        LIMIT {limit}
        """

    if "技能" in question and any(keyword in question for keyword in ["热门", "最多", "统计"]):
        limit = _extract_requested_limit(question, default=10)
        return f"""
        SELECT
            s.skill_name,
            s.category,
            COUNT(js.job_id) AS job_count
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.skill_id
        GROUP BY s.skill_id, s.skill_name, s.category
        ORDER BY job_count DESC
        LIMIT {limit}
        """

    if "岗位类型" in question and any(keyword in question for keyword in ["多少", "数量", "统计"]):
        return """
        SELECT
            j.job_type,
            COUNT(j.job_id) AS job_count
        FROM jobs j
        GROUP BY j.job_type
        ORDER BY job_count DESC
        """

    city = _extract_city(question)
    skill = _extract_skill(question)

    if city and skill:
        return """
        SELECT
            j.job_id,
            c.company_name,
            j.title,
            j.city,
            j.source_url
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        JOIN job_skills js ON js.job_id = j.job_id
        JOIN skills s ON s.skill_id = js.skill_id
        WHERE j.city LIKE '%{city}%'
          AND LOWER(s.skill_name) = LOWER('{skill}')
        ORDER BY j.job_id DESC
        """.format(city=city, skill=skill)

    if city:
        return f"""
        SELECT
            j.job_id,
            c.company_name,
            j.title,
            j.city,
            j.source_url
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        WHERE j.city LIKE '%{city}%'
        ORDER BY j.job_id DESC
        """

    if skill:
        return f"""
        SELECT
            j.job_id,
            c.company_name,
            j.title,
            j.city,
            j.source_url
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        JOIN job_skills js ON js.job_id = j.job_id
        JOIN skills s ON s.skill_id = js.skill_id
        WHERE LOWER(s.skill_name) = LOWER('{skill}')
        ORDER BY j.job_id DESC
        """

    if any(keyword in question for keyword in ["全部岗位", "最新岗位", "岗位列表"]):
        return """
        SELECT
            j.job_id,
            c.company_name,
            j.title,
            j.city,
            j.job_type,
            j.source_url
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        ORDER BY j.job_id DESC
        """

    raise AppError(
        error="TEXT2SQL_FALLBACK_UNSUPPORTED",
        message="大模型暂时不可用，规则兜底无法可靠理解该查询，请稍后重试",
        status_code=503,
    )


def _extract_city(question: str) -> str | None:
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉", "西安", "重庆", "合肥", "苏州"]
    return next((city for city in cities if city in question), None)


def _extract_skill(question: str) -> str | None:
    skills = ["RAG", "Agent", "MCP", "Text2SQL", "Python", "FastAPI", "MySQL"]
    question_lower = question.lower()
    return next((skill for skill in skills if skill.lower() in question_lower), None)


def _extract_requested_limit(question: str, default: int) -> int:
    import re

    match = re.search(r"(?:前|top\s*)(\d+)", question, flags=re.IGNORECASE)
    if match is None:
        return default
    return min(max(int(match.group(1)), 1), 100)
