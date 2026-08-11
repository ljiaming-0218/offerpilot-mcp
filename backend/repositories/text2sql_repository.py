from sqlalchemy import text

from backend.database import engine


def execute_readonly_sql(sql: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text(sql)).mappings().all()

    return [dict(row) for row in rows]