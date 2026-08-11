from typing import Any
import json

from sqlalchemy import text

from backend.database import engine


def create_crawl_task(seed_url: str, source_site: str | None = None) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO crawl_tasks (seed_url, source_site, status)
                VALUES (:seed_url, :source_site, 'running')
                """
            ),
            {
                "seed_url": seed_url,
                "source_site": source_site,
            },
        )

    return result.lastrowid


def finish_crawl_task(task_id: int, status: str, error_message: str | None = None) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE crawl_tasks
                SET status = :status,
                    error_message = :error_message
                WHERE task_id = :task_id
                """
            ),
            {
                "task_id": task_id,
                "status": status,
                "error_message": error_message,
            },
        )


def create_crawl_record(
    task_id: int,
    source_url: str,
    status: str,
    title: str | None = None,
    raw_text: str | None = None,
    parsed_data: dict[str, Any] | None = None,
    job_id: int | None = None,
    error_message: str | None = None,
) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO crawl_records (
                    task_id,
                    job_id,
                    source_url,
                    title,
                    raw_text,
                    parsed_json,
                    status,
                    error_message
                )
                VALUES (
                    :task_id,
                    :job_id,
                    :source_url,
                    :title,
                    :raw_text,
                    :parsed_json,
                    :status,
                    :error_message
                )
                """
            ),
            {
                "task_id": task_id,
                "job_id": job_id,
                "source_url": source_url,
                "title": title,
                "raw_text": raw_text,
                "parsed_json": json.dumps(parsed_data, ensure_ascii=False) if parsed_data else None,
                "status": status,
                "error_message": error_message,
            },
        )

    return result.lastrowid


def list_crawl_tasks(limit: int = 20) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    task_id,
                    seed_url,
                    source_site,
                    status,
                    error_message,
                    CAST(created_at AS CHAR) AS created_at,
                    CAST(updated_at AS CHAR) AS updated_at
                FROM crawl_tasks
                ORDER BY task_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def list_crawl_records(limit: int = 20) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    record_id,
                    task_id,
                    job_id,
                    source_url,
                    title,
                    LEFT(raw_text, 240) AS raw_text_preview,
                    parsed_json,
                    status,
                    error_message,
                    CAST(crawled_at AS CHAR) AS crawled_at
                FROM crawl_records
                ORDER BY record_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    records = []
    for row in rows:
        record = dict(row)
        record["parsed_json"] = _load_json(record.get("parsed_json"))
        records.append(record)

    return records


def _load_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
