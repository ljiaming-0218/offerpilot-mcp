from pydantic import BaseModel, Field, field_validator


class MockInterviewRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=80)
    job_id: int = Field(..., ge=1)
    difficulty: str = Field(default="medium", max_length=30)

    @field_validator("user_id", "difficulty")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value


class InterviewQuestion(BaseModel):
    question_id: int
    question_type: str
    question: str
    why_ask: str
    answer_points: list[str]
    related_evidence: list[str]


class MockInterviewResponse(BaseModel):
    session_id: int
    user_id: str
    job_id: int
    difficulty: str
    job_title: str
    company_name: str
    questions: list[InterviewQuestion]
    created_at: str


class AnswerEvaluationRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    question: str = Field(..., min_length=1)
    user_answer: str = Field(..., min_length=10)

    @field_validator("question", "user_answer")
    @classmethod
    def strip_long_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value


class AnswerEvaluationResponse(BaseModel):
    evaluation_id: int
    session_id: int
    question: str
    user_answer: str
    score: int
    dimension_scores: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    improved_answer: str
    follow_up_questions: list[str]
    created_at: str
