import json
from typing import Any

from sqlalchemy import text

from backend.database import engine


def create_tool_call_log(
    tool_name: str,
    input_data: dict[str, Any],
    output_data: Any,
    status: str,
    error_message: str | None,
    latency_ms: int,
    user_id: str | None = None,
) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO tool_call_logs (
                    user_id,
                    tool_name,
                    input_json,
                    output_json,
                    status,
                    error_message,
                    latency_ms
                )
                VALUES (
                    :user_id,
                    :tool_name,
                    :input_json,
                    :output_json,
                    :status,
                    :error_message,
                    :latency_ms
                )
                """
            ),
            {
                "user_id": user_id,
                "tool_name": tool_name,
                "input_json": json.dumps(input_data, ensure_ascii=False),
                "output_json": json.dumps(output_data, ensure_ascii=False),
                "status": status,
                "error_message": error_message,
                "latency_ms": latency_ms,
            },
        )

    return result.lastrowid


def list_tool_call_logs(limit: int = 20) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    call_id,
                    user_id,
                    tool_name,
                    status,
                    error_message,
                    latency_ms,
                    CAST(created_at AS CHAR) AS created_at
                FROM tool_call_logs
                ORDER BY call_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_tool_call_log(call_id: int) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    call_id,
                    user_id,
                    tool_name,
                    input_json,
                    output_json,
                    status,
                    error_message,
                    latency_ms,
                    CAST(created_at AS CHAR) AS created_at
                FROM tool_call_logs
                WHERE call_id = :call_id
                LIMIT 1
                """
            ),
            {"call_id": call_id},
        ).mappings().first()

    if row is None:
        return None

    result = dict(row)
    result["input"] = _load_json(result.pop("input_json", None))
    result["output"] = _load_json(result.pop("output_json", None))
    return result


def _load_json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
