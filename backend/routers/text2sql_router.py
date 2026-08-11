from fastapi import APIRouter

from backend.schemas.text2sql_schema import Text2SqlRequest, Text2SqlResponse
from backend.services import text2sql_service

router = APIRouter(prefix="/query", tags=["text2sql"])


@router.post("/text2sql", response_model=Text2SqlResponse)
def text2sql_query(payload: Text2SqlRequest) -> dict:
    return text2sql_service.query_jobs_by_question(payload.question)