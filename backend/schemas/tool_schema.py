from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    tool_name: str
    description: str
    risk_level: str
    enabled: bool


class ToolCallRequest(BaseModel):
    input: dict = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    tool_name: str
    success: bool
    result: dict | list | None = None
    error: str | None = None
    message: str | None = None
    call_id: int | None = None


class ToolCallLogItem(BaseModel):
    call_id: int
    user_id: str | None = None
    tool_name: str
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: str