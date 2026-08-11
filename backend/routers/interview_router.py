from fastapi import APIRouter

from backend.schemas.interview_schema import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    MockInterviewRequest,
    MockInterviewResponse,
)
from backend.services import interview_service


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/mock", response_model=MockInterviewResponse)
def generate_mock_interview(payload: MockInterviewRequest) -> dict:
    return interview_service.generate_mock_interview(payload)


@router.post("/evaluate", response_model=AnswerEvaluationResponse)
def evaluate_answer(payload: AnswerEvaluationRequest) -> dict:
    return interview_service.evaluate_answer(payload)
