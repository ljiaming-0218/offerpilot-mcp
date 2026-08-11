import json
from typing import Any

from sqlalchemy import text

from backend.database import engine


def upsert_user_profile(profile: dict[str, Any]) -> dict[str, Any]:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO user_profiles (
                    user_id,
                    owner_user_id,
                    name,
                    education,
                    target_roles,
                    target_cities,
                    preferred_work_type,
                    skills_json,
                    projects_json,
                    weaknesses_json
                )
                VALUES (
                    :user_id,
                    :owner_user_id,
                    :name,
                    :education,
                    :target_roles,
                    :target_cities,
                    :preferred_work_type,
                    :skills_json,
                    :projects_json,
                    :weaknesses_json
                )
                ON DUPLICATE KEY UPDATE
                    owner_user_id = VALUES(owner_user_id),
                    name = VALUES(name),
                    education = VALUES(education),
                    target_roles = VALUES(target_roles),
                    target_cities = VALUES(target_cities),
                    preferred_work_type = VALUES(preferred_work_type),
                    skills_json = VALUES(skills_json),
                    projects_json = VALUES(projects_json),
                    weaknesses_json = VALUES(weaknesses_json)
                """
            ),
            _to_db_row(profile),
        )

    saved = get_user_profile(profile["user_id"])
    if saved is None:
        raise RuntimeError("用户画像保存成功，但读取失败")
    return saved


def get_user_profile(user_id: str) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    p.user_id,
                    p.owner_user_id,
                    u.username AS owner_username,
                    p.name,
                    p.education,
                    p.target_roles,
                    p.target_cities,
                    p.preferred_work_type,
                    p.skills_json,
                    p.projects_json,
                    p.weaknesses_json,
                    CAST(p.created_at AS CHAR) AS created_at,
                    CAST(p.updated_at AS CHAR) AS updated_at
                FROM user_profiles p
                LEFT JOIN app_users u ON u.user_id = p.owner_user_id
                WHERE p.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).mappings().first()

    return _from_db_row(dict(row)) if row else None


def list_user_profiles(owner_user_id: int | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    where_sql = ""
    if owner_user_id is not None:
        where_sql = "WHERE p.owner_user_id = :owner_user_id"
        params["owner_user_id"] = owner_user_id

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT
                    p.user_id,
                    p.owner_user_id,
                    u.username AS owner_username,
                    p.name,
                    p.education,
                    p.target_roles,
                    p.target_cities,
                    p.preferred_work_type,
                    p.skills_json,
                    p.projects_json,
                    p.weaknesses_json,
                    CAST(p.created_at AS CHAR) AS created_at,
                    CAST(p.updated_at AS CHAR) AS updated_at
                FROM user_profiles p
                LEFT JOIN app_users u ON u.user_id = p.owner_user_id
                {where_sql}
                ORDER BY p.updated_at DESC, p.user_id ASC
                """
            ),
            params,
        ).mappings().all()

    return [_from_db_row(dict(row)) for row in rows]


def _to_db_row(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": profile["user_id"],
        "owner_user_id": profile.get("owner_user_id"),
        "name": profile.get("name"),
        "education": profile.get("education"),
        "target_roles": json.dumps(profile.get("target_roles", []), ensure_ascii=False),
        "target_cities": json.dumps(profile.get("target_cities", []), ensure_ascii=False),
        "preferred_work_type": profile.get("preferred_work_type"),
        "skills_json": json.dumps(profile.get("skills", []), ensure_ascii=False),
        "projects_json": json.dumps(profile.get("projects", []), ensure_ascii=False),
        "weaknesses_json": json.dumps(profile.get("weaknesses", []), ensure_ascii=False),
    }


def _from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "owner_user_id": row.get("owner_user_id"),
        "owner_username": row.get("owner_username"),
        "name": row.get("name"),
        "education": row.get("education"),
        "target_roles": _loads_list(row.get("target_roles")),
        "target_cities": _loads_list(row.get("target_cities")),
        "preferred_work_type": row.get("preferred_work_type"),
        "skills": _loads_list(row.get("skills_json")),
        "projects": _loads_list(row.get("projects_json")),
        "weaknesses": _loads_list(row.get("weaknesses_json")),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
