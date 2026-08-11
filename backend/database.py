from pathlib import Path
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.config import settings


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [sql.strip() for sql in schema_sql.split(";") if sql.strip()]

    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        _ensure_optional_columns(connection)


def _ensure_optional_columns(connection) -> None:
    requirement_column_exists = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'jobs'
              AND COLUMN_NAME = 'requirement_json'
            """
        )
    ).scalar()

    if not requirement_column_exists:
        connection.exec_driver_sql("ALTER TABLE jobs ADD COLUMN requirement_json TEXT")

    profile_owner_column_exists = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_profiles'
              AND COLUMN_NAME = 'owner_user_id'
            """
        )
    ).scalar()

    if not profile_owner_column_exists:
        connection.exec_driver_sql("ALTER TABLE user_profiles ADD COLUMN owner_user_id BIGINT")

    profile_owner_index_exists = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_profiles'
              AND INDEX_NAME = 'idx_user_profiles_owner_user_id'
            """
        )
    ).scalar()

    if not profile_owner_index_exists:
        connection.exec_driver_sql("CREATE INDEX idx_user_profiles_owner_user_id ON user_profiles(owner_user_id)")


def verify_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def iter_table_names() -> Iterator[str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SHOW TABLES")).fetchall()

    for row in rows:
        yield row[0]
