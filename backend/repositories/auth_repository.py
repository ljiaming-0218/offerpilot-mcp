from typing import Any

from sqlalchemy import text

from backend.database import engine


def count_users() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT COUNT(*) FROM app_users")).scalar() or 0


def create_user(username: str, password_hash: str, role: str, display_name: str | None) -> dict[str, Any]:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO app_users (username, password_hash, role, display_name)
                VALUES (:username, :password_hash, :role, :display_name)
                """
            ),
            {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "display_name": display_name,
            },
        )
        user_id = result.lastrowid

    user = get_user_by_id(user_id)
    if user is None:
        raise RuntimeError("用户创建成功，但读取失败")
    return user


def get_user_by_username(username: str) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    user_id,
                    username,
                    password_hash,
                    role,
                    display_name,
                    CAST(created_at AS CHAR) AS created_at
                FROM app_users
                WHERE username = :username
                """
            ),
            {"username": username},
        ).mappings().first()

    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    user_id,
                    username,
                    role,
                    display_name,
                    CAST(created_at AS CHAR) AS created_at
                FROM app_users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).mappings().first()

    return dict(row) if row else None
