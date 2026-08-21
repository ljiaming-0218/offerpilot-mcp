from fastapi import APIRouter, Depends

from backend.dependencies import get_admin_user, get_current_user
from backend.agent import intent_router
from backend.schemas.agent_schema import AgentRouteRequest, AgentRouteResult
from backend.agent import executor
from backend.schemas.agent_schema import AgentRunRequest, AgentRunResult
from backend.repositories import agent_trace_repository
from backend.errors import AppError
from backend.schemas.agent_schema import AgentTraceDetail, AgentTraceListItem

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/route", response_model=AgentRouteResult)
def route_task(payload: AgentRouteRequest, current_user: dict = Depends(get_admin_user)) -> dict:
    return intent_router.route_task(payload.task)


@router.post("/run", response_model=AgentRunResult)
def run_agent(payload: AgentRunRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return executor.run_agent(payload.task, current_user=current_user)

@router.get("/traces", response_model=list[AgentTraceListItem])
def list_agent_traces(limit: int = 20, current_user: dict = Depends(get_admin_user)) -> list[dict]:
    return agent_trace_repository.list_agent_traces(limit=limit)


@router.get("/traces/{trace_id}", response_model=AgentTraceDetail)
def get_agent_trace(trace_id: int, current_user: dict = Depends(get_admin_user)) -> dict:
    trace = agent_trace_repository.get_agent_trace(trace_id)
    if trace is None:
        raise AppError(
            error="TRACE_NOT_FOUND",
            message="运行记录不存在",
            status_code=404,
        )
    return trace
