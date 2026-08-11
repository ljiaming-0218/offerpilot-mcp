import json
from typing import Any

from sqlalchemy import text

from backend.database import engine


def create_interview_session(
    user_id: str,
    job_id: int,
    difficulty: str,
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO interview_sessions (
                    user_id, job_id, difficulty, questions_json
                )
                VALUES (
                    :user_id, :job_id, :difficulty, :questions_json
                )
                """
            ),
            {
                "user_id": user_id,
                "job_id": job_id,
                "difficulty": difficulty,
                "questions_json": json.dumps(questions, ensure_ascii=False),
            },
        )
        session_id = result.lastrowid

    saved = get_interview_session(session_id)
    if saved is None:
        raise RuntimeError("面试会话保存成功，但读取失败")
    return saved


def get_interview_session(session_id: int) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    session_id,
                    user_id,
                    job_id,
                    difficulty,
                    questions_json,
                    CAST(created_at AS CHAR) AS created_at
                FROM interview_sessions
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id},
        ).mappings().first()

    return _from_db_row(dict(row)) if row else None


def create_answer_evaluation(
    session_id: int,
    question: str,
    user_answer: str,
    score: int,
    dimension_scores: dict[str, int],
    strengths: list[str],
    weaknesses: list[str],
    improved_answer: str,
    follow_up_questions: list[str],
) -> dict[str, Any]:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO answer_evaluations (
                    session_id,
                    question,
                    user_answer,
                    score,
                    dimension_scores_json,
                    strengths_json,
                    weaknesses_json,
                    improved_answer,
                    follow_up_questions_json
                )
                VALUES (
                    :session_id,
                    :question,
                    :user_answer,
                    :score,
                    :dimension_scores_json,
                    :strengths_json,
                    :weaknesses_json,
                    :improved_answer,
                    :follow_up_questions_json
                )
                """
            ),
            {
                "session_id": session_id,
                "question": question,
                "user_answer": user_answer,
                "score": score,
                "dimension_scores_json": json.dumps(dimension_scores, ensure_ascii=False),
                "strengths_json": json.dumps(strengths, ensure_ascii=False),
                "weaknesses_json": json.dumps(weaknesses, ensure_ascii=False),
                "improved_answer": improved_answer,
                "follow_up_questions_json": json.dumps(follow_up_questions, ensure_ascii=False),
            },
        )
        evaluation_id = result.lastrowid

    saved = get_answer_evaluation(evaluation_id)
    if saved is None:
        raise RuntimeError("回答评分保存成功，但读取失败")
    return saved


def get_answer_evaluation(evaluation_id: int) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    evaluation_id,
                    session_id,
                    question,
                    user_answer,
                    score,
                    dimension_scores_json,
                    strengths_json,
                    weaknesses_json,
                    improved_answer,
                    follow_up_questions_json,
                    CAST(created_at AS CHAR) AS created_at
                FROM answer_evaluations
                WHERE evaluation_id = :evaluation_id
                """
            ),
            {"evaluation_id": evaluation_id},
        ).mappings().first()

    return _evaluation_from_db_row(dict(row)) if row else None


def _from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    try:
        questions = json.loads(row.get("questions_json") or "[]")
    except json.JSONDecodeError:
        questions = []

    return {
        "session_id": row["session_id"],
        "user_id": row["user_id"],
        "job_id": row["job_id"],
        "difficulty": row["difficulty"],
        "questions": questions if isinstance(questions, list) else [],
        "created_at": row["created_at"],
    }


def _evaluation_from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_id": row["evaluation_id"],
        "session_id": row["session_id"],
        "question": row["question"],
        "user_answer": row["user_answer"],
        "score": row["score"],
        "dimension_scores": _loads(row.get("dimension_scores_json"), {}),
        "strengths": _loads(row.get("strengths_json"), []),
        "weaknesses": _loads(row.get("weaknesses_json"), []),
        "improved_answer": row["improved_answer"],
        "follow_up_questions": _loads(row.get("follow_up_questions_json"), []),
        "created_at": row["created_at"],
    }


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
