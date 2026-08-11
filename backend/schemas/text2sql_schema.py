from pydantic import BaseModel, Field


class SqlGuardRequest(BaseModel):
    sql: str = Field(..., min_length=1)


class SqlGuardResult(BaseModel):
    safe: bool
    sql: str
    reason: str


class Text2SqlRequest(BaseModel):
    question: str = Field(..., min_length=1)


class Text2SqlResponse(BaseModel):
    question: str
    sql: str
    safe: bool
    reason: str
    rows: list[dict]