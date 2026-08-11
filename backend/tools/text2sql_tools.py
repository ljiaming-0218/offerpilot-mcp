from backend.services import text2sql_service


def text2sql_query(input_data: dict) -> dict:
    question = input_data.get("question", "")
    return text2sql_service.query_jobs_by_question(question)