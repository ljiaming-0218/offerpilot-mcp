import json
from typing import Any

from sqlalchemy import text

from backend.database import engine


def create_agent_trace(
    task: str,
    skill_name: str,
    trace: list[dict[str, Any]],
    final_answer: str,
    user_id: str | None = None,
) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO agent_traces (
                    user_id,
                    task,
                    skill_name,
                    trace_json,
                    final_answer
                )
                VALUES (
                    :user_id,
                    :task,
                    :skill_name,
                    :trace_json,
                    :final_answer
                )
                """
            ),
            {
                "user_id": user_id,
                "task": task,
                "skill_name": skill_name,
                "trace_json": json.dumps(trace, ensure_ascii=False),
                "final_answer": final_answer,
            },
        )

    return result.lastrowid


def list_agent_traces(limit: int = 20) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    trace_id,
                    user_id,
                    task,
                    skill_name,
                    final_answer,
                    CAST(created_at AS CHAR) AS created_at
                FROM agent_traces
                ORDER BY trace_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]