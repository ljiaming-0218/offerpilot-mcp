from backend.errors import AppError
from backend.repositories import text2sql_repository
from backend.services import sql_guard_service


def query_jobs_by_question(question: str) -> dict:
    raw_sql = _generate_sql_by_rules(question)
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
        "safe": guard_result["safe"],
        "reason": guard_result["reason"],
        "rows": rows,
    }


def _generate_sql_by_rules(question: str) -> str:
    question = question.strip()

    if "热门技能" in question or "最多的技能" in question or "技能统计" in question:
        return """
        SELECT
            s.skill_name,
            s.category,
            COUNT(js.job_id) AS job_count
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.skill_id
        GROUP BY s.skill_id, s.skill_name, s.category
        ORDER BY job_count DESC
        """

    if "成都" in question and ("RAG" in question or "rag" in question):
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
        WHERE j.city LIKE '%成都%'
          AND s.skill_name = 'RAG'
        ORDER BY j.job_id DESC
        """

    if "成都" in question:
        return """
        SELECT
            j.job_id,
            c.company_name,
            j.title,
            j.city,
            j.source_url
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        WHERE j.city LIKE '%成都%'
        ORDER BY j.job_id DESC
        """

    if "RAG" in question or "rag" in question:
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
        WHERE s.skill_name = 'RAG'
        ORDER BY j.job_id DESC
        """

    return """
    SELECT
        j.job_id,
        c.company_name,
        j.title,
        j.city,
        j.source_url
    FROM jobs j
    JOIN companies c ON c.company_id = j.company_id
    ORDER BY j.job_id DESC
    """