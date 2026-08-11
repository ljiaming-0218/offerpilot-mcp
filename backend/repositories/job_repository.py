from typing import Any
import json

from sqlalchemy import text

from backend.database import engine


def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    with engine.begin() as connection:
        company_id = _get_or_create_company(
            connection=connection,
            company_name=payload["company_name"],
            industry=payload.get("industry"),
            city=payload.get("city"),
        )

        result = connection.execute(
            text(
                """
                INSERT INTO jobs (
                    company_id, title, city, job_type, source_url, description
                )
                VALUES (
                    :company_id, :title, :city, :job_type, :source_url, :description
                )
                """
            ),
            {
                "company_id": company_id,
                "title": payload["title"],
                "city": payload.get("city"),
                "job_type": payload.get("job_type"),
                "source_url": payload.get("source_url"),
                "description": payload["description"],
            },
        )

        job_id = result.lastrowid
        created_job = _get_job_by_id_with_connection(connection, job_id)

        if created_job is None:
            raise RuntimeError("岗位创建成功，但读取失败")

        return created_job


def list_jobs() -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    j.company_id,
                    c.company_name,
                    j.title,
                    j.city,
                    j.job_type,
                    j.source_url,
                    LEFT(j.description, 120) AS description_preview,
                    CAST(j.created_at AS CHAR) AS created_at
                FROM jobs j
                JOIN companies c ON c.company_id = j.company_id
                ORDER BY j.created_at DESC, j.job_id DESC
                """
            )
        ).mappings().all()

    return [dict(row) for row in rows]


def _get_job_by_id_with_connection(connection, job_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        text(
            """
            SELECT
                j.job_id,
                j.company_id,
                c.company_name,
                c.industry,
                j.title,
                j.city,
                j.job_type,
                j.source_url,
                j.requirement_json,
                j.description,
                CAST(j.created_at AS CHAR) AS created_at,
                CAST(j.updated_at AS CHAR) AS updated_at
            FROM jobs j
            JOIN companies c ON c.company_id = j.company_id
            WHERE j.job_id = :job_id
            """
        ),
        {"job_id": job_id},
    ).mappings().first()

    return _parse_job_row(dict(row)) if row else None

def get_job_by_id(job_id: int) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    j.company_id,
                    c.company_name,
                    c.industry,
                    j.title,
                    j.city,
                    j.job_type,
                    j.source_url,
                    j.requirement_json,
                    j.description,
                    CAST(j.created_at AS CHAR) AS created_at,
                    CAST(j.updated_at AS CHAR) AS updated_at
                FROM jobs j
                JOIN companies c ON c.company_id = j.company_id
                WHERE j.job_id = :job_id
                """
            ),
            {"job_id": job_id},
        ).mappings().first()

    return _parse_job_row(dict(row)) if row else None


def save_job_requirement(job_id: int, requirement: dict[str, Any]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE jobs
                SET requirement_json = :requirement_json
                WHERE job_id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "requirement_json": json.dumps(requirement, ensure_ascii=False),
            },
        )


def _get_or_create_company(connection, company_name: str, industry: str | None, city: str | None) -> int:
    row = connection.execute(
        text(
            """
            SELECT company_id
            FROM companies
            WHERE company_name = :company_name
            """
        ),
        {"company_name": company_name},
    ).mappings().first()

    if row:
        connection.execute(
            text(
                """
                UPDATE companies
                SET
                    industry = COALESCE(:industry, industry),
                    city = COALESCE(:city, city)
                WHERE company_id = :company_id
                """
            ),
            {
                "industry": industry,
                "city": city,
                "company_id": row["company_id"],
            },
        )
        return row["company_id"]

    result = connection.execute(
        text(
            """
            INSERT INTO companies (company_name, industry, city)
            VALUES (:company_name, :industry, :city)
            """
        ),
        {
            "company_name": company_name,
            "industry": industry,
            "city": city,
        },
    )

    return result.lastrowid


def find_duplicate_job(payload: dict[str, Any]) -> dict[str, Any] | None:
    with engine.connect() as connection:
        if payload.get("source_url"):
            row = connection.execute(
                text(
                    """
                    SELECT
                        j.job_id,
                        j.company_id,
                        c.company_name,
                        c.industry,
                        j.title,
                        j.city,
                        j.job_type,
                        j.source_url,
                        j.description,
                        CAST(j.created_at AS CHAR) AS created_at,
                        CAST(j.updated_at AS CHAR) AS updated_at
                    FROM jobs j
                    JOIN companies c ON c.company_id = j.company_id
                    WHERE j.source_url = :source_url
                    LIMIT 1
                    """
                ),
                {"source_url": payload["source_url"]},
            ).mappings().first()

            if row:
                return dict(row)

        row = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    j.company_id,
                    c.company_name,
                    c.industry,
                    j.title,
                    j.city,
                    j.job_type,
                    j.source_url,
                    j.description,
                    CAST(j.created_at AS CHAR) AS created_at,
                    CAST(j.updated_at AS CHAR) AS updated_at
                FROM jobs j
                JOIN companies c ON c.company_id = j.company_id
                WHERE c.company_name = :company_name
                  AND j.title = :title
                  AND COALESCE(j.city, '') = COALESCE(:city, '')
                LIMIT 1
                """
            ),
            {
                "company_name": payload["company_name"],
                "title": payload["title"],
                "city": payload.get("city"),
            },
        ).mappings().first()

    return dict(row) if row else None

def list_jobs_without_skills(limit: int = 20) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    j.title,
                    j.description
                FROM jobs j
                LEFT JOIN job_skills js ON js.job_id = j.job_id
                WHERE js.job_id IS NULL
                ORDER BY j.job_id ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def list_jobs_without_requirement(limit: int = 20) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    j.title,
                    j.description
                FROM jobs j
                WHERE j.requirement_json IS NULL
                   OR j.requirement_json = ''
                ORDER BY j.job_id ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def _parse_job_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_requirement = row.get("requirement_json")
    if raw_requirement:
        try:
            row["requirement_json"] = json.loads(raw_requirement)
        except json.JSONDecodeError:
            row["requirement_json"] = None
    else:
        row["requirement_json"] = None
    return row


def list_jobs_with_skills() -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    j.job_id,
                    c.company_name,
                    j.title,
                    j.city,
                    j.job_type,
                    j.source_url,
                    j.requirement_json,
                    s.skill_name,
                    s.category,
                    js.importance
                FROM jobs j
                JOIN companies c ON c.company_id = j.company_id
                JOIN job_skills js ON js.job_id = j.job_id
                JOIN skills s ON s.skill_id = js.skill_id
                ORDER BY j.created_at DESC, j.job_id DESC, s.skill_name ASC
                """
            )
        ).mappings().all()

    jobs: dict[int, dict[str, Any]] = {}
    for row in rows:
        job_id = row["job_id"]
        if job_id not in jobs:
            jobs[job_id] = {
                "job_id": job_id,
                "company_name": row["company_name"],
                "title": row["title"],
                "city": row["city"],
                "job_type": row["job_type"],
                "source_url": row["source_url"],
                "requirement_json": _load_requirement(row.get("requirement_json")),
                "skills": [],
            }

        jobs[job_id]["skills"].append(
            {
                "skill_name": row["skill_name"],
                "category": row["category"],
                "importance": row["importance"],
            }
        )

    return list(jobs.values())


def _load_requirement(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
