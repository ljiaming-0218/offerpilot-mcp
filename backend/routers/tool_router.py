from fastapi import APIRouter, Depends
from backend.dependencies import get_admin_user
from backend.errors import AppError
from backend.repositories import tool_log_repository
from backend.schemas.tool_schema import ToolCallLogDetail, ToolCallLogItem
from backend.schemas.tool_schema import ToolCallRequest, ToolCallResponse, ToolInfo
from backend.tools import registry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolInfo])
def list_tools(current_user: dict = Depends(get_admin_user)) -> list[dict]:
    return registry.list_tools()

@router.get("/logs", response_model=list[ToolCallLogItem])
def list_tool_logs(limit: int = 20, current_user: dict = Depends(get_admin_user)) -> list[dict]:
    return tool_log_repository.list_tool_call_logs(limit=limit)


@router.get("/logs/{call_id}", response_model=ToolCallLogDetail)
def get_tool_log(call_id: int, current_user: dict = Depends(get_admin_user)) -> dict:
    log = tool_log_repository.get_tool_call_log(call_id)
    if log is None:
        raise AppError(
            error="TOOL_LOG_NOT_FOUND",
            message="工具调用日志不存在",
            status_code=404,
        )
    return log

@router.post("/{tool_name}/call", response_model=ToolCallResponse)
def call_tool(
    tool_name: str,
    payload: ToolCallRequest,
    current_user: dict = Depends(get_admin_user),
) -> dict:
    return registry.call_tool(tool_name, payload.input, user_id=str(current_user["user_id"]))

