import re

from sqlglot import exp, parse
from sqlglot.errors import ParseError


MAX_RESULT_ROWS = 100

ALLOWED_COLUMNS = {
    "companies": {
        "company_id", "company_name", "industry", "city", "created_at", "updated_at",
    },
    "jobs": {
        "job_id", "company_id", "title", "city", "job_type", "source_url",
        "requirement_json", "description", "created_at", "updated_at",
    },
    "skills": {"skill_id", "skill_name", "category", "created_at"},
    "job_skills": {"job_id", "skill_id", "importance"},
}

ALLOWED_FUNCTIONS = {
    "avg",
    "coalesce",
    "count",
    "date",
    "json_extract",
    "json_unquote",
    "lower",
    "max",
    "min",
    "month",
    "sum",
    "upper",
    "year",
}


def check_sql_safety(sql: str) -> dict:
    normalized_sql = " ".join(sql.strip().split())

    if not normalized_sql:
        return _unsafe(sql=normalized_sql, reason="SQL 不能为空")

    if _has_comment(normalized_sql):
        return _unsafe(sql=normalized_sql, reason="SQL 不允许包含注释")

    if ";" in normalized_sql:
        return _unsafe(sql=normalized_sql, reason="SQL 不允许包含分号或多语句")

    try:
        expressions = parse(normalized_sql, read="mysql")
    except ParseError as exc:
        return _unsafe(sql=normalized_sql, reason=f"SQL 语法无法解析：{str(exc)[:120]}")

    if len(expressions) != 1 or not isinstance(expressions[0], exp.Select):
        return _unsafe(sql=normalized_sql, reason="只允许单条 SELECT 查询")

    expression = expressions[0]
    if expression.args.get("with_") is not None:
        return _unsafe(sql=normalized_sql, reason="不允许使用 WITH 查询")

    if expression.find(exp.Subquery) is not None:
        return _unsafe(sql=normalized_sql, reason="不允许使用子查询")

    if expression.args.get("locks"):
        return _unsafe(sql=normalized_sql, reason="不允许使用锁定读取")

    if expression.find(exp.SessionParameter) is not None or expression.find(exp.Parameter) is not None:
        return _unsafe(sql=normalized_sql, reason="不允许读取数据库会话变量")

    table_error = _validate_tables(expression)
    if table_error:
        return _unsafe(sql=normalized_sql, reason=table_error)

    column_error = _validate_columns(expression)
    if column_error:
        return _unsafe(sql=normalized_sql, reason=column_error)

    function_error = _validate_functions(expression)
    if function_error:
        return _unsafe(sql=normalized_sql, reason=function_error)

    safe_expression = _apply_limit(expression)
    return {
        "safe": True,
        "sql": safe_expression.sql(dialect="mysql"),
        "reason": "SQL 通过 AST 安全检查",
    }


def _validate_tables(expression: exp.Select) -> str | None:
    tables = list(expression.find_all(exp.Table))
    if not tables:
        return "SQL 必须查询业务数据表"

    for table in tables:
        table_name = table.name.lower()
        if table.db or table.catalog:
            return "不允许跨数据库或访问系统 Schema"
        if table_name not in ALLOWED_COLUMNS:
            return f"不允许访问数据表：{table_name}"
    return None


def _validate_columns(expression: exp.Select) -> str | None:
    alias_to_table = {
        table.alias_or_name.lower(): table.name.lower()
        for table in expression.find_all(exp.Table)
    }
    all_columns = set().union(*ALLOWED_COLUMNS.values())
    select_aliases = {
        projection.alias.lower()
        for projection in expression.expressions
        if projection.alias
    }

    for column in expression.find_all(exp.Column):
        column_name = column.name.lower()
        if column_name == "*":
            continue

        if column.table:
            table_name = alias_to_table.get(column.table.lower())
            if table_name is None:
                return f"无法识别字段所属表：{column.table}"
            if column_name not in ALLOWED_COLUMNS[table_name]:
                return f"字段不属于允许的表：{column.sql(dialect='mysql')}"
        elif column_name not in all_columns and column_name not in select_aliases:
            return f"不允许查询字段：{column_name}"
    return None


def _validate_functions(expression: exp.Select) -> str | None:
    for function in expression.find_all(exp.Func):
        if isinstance(function, exp.Anonymous):
            function_name = function.name.lower()
        else:
            function_name = function.sql_name().lower()
        if function_name not in ALLOWED_FUNCTIONS:
            return f"不允许使用 SQL 函数：{function_name}"
    return None


def _apply_limit(expression: exp.Select) -> exp.Select:
    limit = expression.args.get("limit")
    if limit is None:
        return expression.limit(MAX_RESULT_ROWS)

    limit_value = limit.expression
    if not isinstance(limit_value, exp.Literal) or not limit_value.is_int:
        return expression.limit(MAX_RESULT_ROWS)

    if int(limit_value.name) > MAX_RESULT_ROWS:
        return expression.limit(MAX_RESULT_ROWS)
    return expression


def _has_comment(sql: str) -> bool:
    return bool(re.search(r"(--|/\*|\*/|#)", sql))


def _unsafe(sql: str, reason: str) -> dict:
    return {
        "safe": False,
        "sql": sql,
        "reason": reason,
    }
