from fastapi import APIRouter

from backend.agent import intent_router
from backend.schemas.agent_schema import AgentRouteRequest, AgentRouteResult
from backend.agent import executor
from backend.schemas.agent_schema import AgentRunRequest, AgentRunResult
from backend.repositories import agent_trace_repository
from backend.schemas.agent_schema import AgentTraceListItem

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/route", response_model=AgentRouteResult)
def route_task(payload: AgentRouteRequest) -> dict:
    return intent_router.route_task(payload.task)


@router.post("/run", response_model=AgentRunResult)
def run_agent(payload: AgentRunRequest) -> dict:
    return executor.run_agent(payload.task)

@router.get("/traces", response_model=list[AgentTraceListItem])
def list_agent_traces(limit: int = 20) -> list[dict]:
    return agent_trace_repository.list_agent_traces(limit=limit)