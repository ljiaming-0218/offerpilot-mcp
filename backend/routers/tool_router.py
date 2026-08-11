from fastapi import APIRouter
from backend.repositories import tool_log_repository
from backend.schemas.tool_schema import ToolCallLogItem
from backend.schemas.tool_schema import ToolCallRequest, ToolCallResponse, ToolInfo
from backend.tools import registry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolInfo])
def list_tools() -> list[dict]:
    return registry.list_tools()

@router.get("/logs", response_model=list[ToolCallLogItem])
def list_tool_logs(limit: int = 20) -> list[dict]:
    return tool_log_repository.list_tool_call_logs(limit=limit)

@router.post("/{tool_name}/call", response_model=ToolCallResponse)
def call_tool(tool_name: str, payload: ToolCallRequest) -> dict:
    return registry.call_tool(tool_name, payload.input)

