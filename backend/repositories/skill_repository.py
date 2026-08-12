

from sqlalchemy import text

from backend.database import engine







def save_job_skills(job_id: int, skills: list[dict]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM job_skills WHERE job_id = :job_id"),
            {"job_id": job_id},
        )

        for skill in skills:
            skill_id = _get_or_create_skill(
                connection=connection,
                skill_name=skill["skill_name"],
                category=skill["category"],
            )

            connection.execute(
                text(
                    """
                    INSERT INTO job_skills (job_id, skill_id, importance)
                    VALUES (:job_id, :skill_id, :importance)
                    ON DUPLICATE KEY UPDATE
                        importance = VALUES(importance)
                    """
                ),
                {
                    "job_id": job_id,
                    "skill_id": skill_id,
                    "importance": skill["importance"],
                },
            )


def _get_or_create_skill(connection, skill_name: str, category: str) -> int:
    row = connection.execute(
        text(
            """
            SELECT skill_id
            FROM skills
            WHERE skill_name = :skill_name
            """
        ),
        {"skill_name": skill_name},
    ).mappings().first()

    if row:
        return row["skill_id"]

    result = connection.execute(
        text(
            """
            INSERT INTO skills (skill_name, category)
            VALUES (:skill_name, :category)
            """
        ),
        {
            "skill_name": skill_name,
            "category": category,
        },
    )

    return result.lastrowid



def list_skills() -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    s.skill_id,
                    s.skill_name,
                    s.category,
                    COUNT(js.job_id) AS job_count
                FROM skills s
                LEFT JOIN job_skills js ON js.skill_id = s.skill_id
                GROUP BY s.skill_id, s.skill_name, s.category
                ORDER BY job_count DESC, s.skill_name ASC
                """
            )
        ).mappings().all()

    return [dict(row) for row in rows]


def list_skills_for_job(job_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    s.skill_id,
                    s.skill_name,
                    s.category,
                    js.importance
                FROM job_skills js
                JOIN skills s ON s.skill_id = js.skill_id
                WHERE js.job_id = :job_id
                ORDER BY js.importance DESC, s.skill_name ASC
                """
            ),
            {"job_id": job_id},
        ).mappings().all()

    return [dict(row) for row in rows]
