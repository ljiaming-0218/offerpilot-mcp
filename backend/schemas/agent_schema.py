from pydantic import BaseModel, Field


class AgentRouteRequest(BaseModel):
    task: str = Field(..., min_length=1)


class AgentRouteResult(BaseModel):
    task: str
    skill_name: str
    reason: str

class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1)


class AgentTraceStep(BaseModel):
    step: int
    type: str
    content: str
    reason: str | None = None
    skill_name: str | None = None
    tool_name: str | None = None
    input: dict | None = None
    output: dict | list | None = None
    call_id: int | None = None



class AgentRunResult(BaseModel):
    task: str
    skill_name: str
    final_answer: str
    trace_id: int | None = None
    trace: list[AgentTraceStep]


class AgentTraceListItem(BaseModel):
    trace_id: int
    user_id: str | None = None
    task: str
    skill_name: str | None = None
    final_answer: str | None = None
    created_at: str