from fastapi import APIRouter, Depends

from backend.dependencies import get_current_user
from backend.schemas.interview_schema import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    MockInterviewRequest,
    MockInterviewResponse,
)
from backend.services import interview_service


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/mock", response_model=MockInterviewResponse)
def generate_mock_interview(
    payload: MockInterviewRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return interview_service.generate_mock_interview(payload, current_user=current_user)


@router.post("/evaluate", response_model=AnswerEvaluationResponse)
def evaluate_answer(
    payload: AnswerEvaluationRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return interview_service.evaluate_answer(payload, current_user=current_user)
