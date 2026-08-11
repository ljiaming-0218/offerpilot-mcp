import re


DANGEROUS_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace",
    "grant",
    "revoke",
}


def check_sql_safety(sql: str) -> dict:
    normalized_sql = _normalize_sql(sql)

    if not normalized_sql:
        return _unsafe(sql=normalized_sql, reason="SQL 不能为空")

    if _has_comment(normalized_sql):
        return _unsafe(sql=normalized_sql, reason="SQL 不允许包含注释")

    if ";" in normalized_sql:
        return _unsafe(sql=normalized_sql, reason="SQL 不允许包含分号或多语句")

    if not normalized_sql.lower().startswith("select "):
        return _unsafe(sql=normalized_sql, reason="只允许 SELECT 查询")

    dangerous_keyword = _find_dangerous_keyword(normalized_sql)
    if dangerous_keyword:
        return _unsafe(
            sql=normalized_sql,
            reason=f"SQL 包含危险关键字：{dangerous_keyword.upper()}",
        )

    safe_sql = _ensure_limit(normalized_sql)

    return {
        "safe": True,
        "sql": safe_sql,
        "reason": "SQL 通过安全检查",
    }


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def _has_comment(sql: str) -> bool:
    return "--" in sql or "/*" in sql or "*/" in sql or "#" in sql


def _find_dangerous_keyword(sql: str) -> str | None:
    sql_lower = sql.lower()

    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_lower):
            return keyword

    return None


def _ensure_limit(sql: str) -> str:
    if re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        return sql

    return f"{sql} LIMIT 100"


def _unsafe(sql: str, reason: str) -> dict:
    return {
        "safe": False,
        "sql": sql,
        "reason": reason,
    }
