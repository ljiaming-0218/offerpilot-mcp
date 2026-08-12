
import time

from backend.errors import AppError
from backend.repositories import tool_log_repository

from backend.tools.base import ToolDefinition
from backend.tools.crawler_tools import crawl_job_url
from backend.tools.job_tools import extract_skills, search_jobs
from backend.tools.skill_tools import list_skills
from backend.tools.text2sql_tools import text2sql_query


TOOLS = {
    "search_jobs": ToolDefinition(
        tool_name="search_jobs",
        description="查询岗位列表",
        risk_level="low",
        enabled=True,
        callable_function=search_jobs,
    ),
    "list_skills": ToolDefinition(
        tool_name="list_skills",
        description="查询技能统计列表",
        risk_level="low",
        enabled=True,
        callable_function=list_skills,
    ),
    "text2sql_query": ToolDefinition(
        tool_name="text2sql_query",
        description="自然语言查询岗位数据库，执行前会经过 SQL Guard",
        risk_level="medium",
        enabled=True,
        callable_function=text2sql_query,
    ),
    "crawl_job_url": ToolDefinition(
        tool_name="crawl_job_url",
        description="采集公开岗位详情页并写入岗位库",
        risk_level="medium",
        enabled=True,
        callable_function=crawl_job_url,
    ),
    "extract_skills": ToolDefinition(
        tool_name="extract_skills",
        description="抽取指定岗位的技能标签并写入 skills/job_skills",
        risk_level="medium",
        enabled=True,
        callable_function=extract_skills,
    ),
}


def list_tools() -> list[dict]:
    return [
        {
            "tool_name": tool.tool_name,
            "description": tool.description,
            "risk_level": tool.risk_level,
            "enabled": tool.enabled,
        }
        for tool in TOOLS.values()
    ]


def call_tool(tool_name: str, input_data: dict, user_id: str | None = None) -> dict:
    started_at = time.perf_counter()
    tool = TOOLS.get(tool_name)

    if tool is None:
        raise AppError(
            error="TOOL_NOT_FOUND",
            message="工具不存在",
            status_code=404,
        )

    if not tool.enabled:
        raise AppError(
            error="TOOL_DISABLED",
            message="工具已禁用",
            status_code=403,
        )

    try:
        result = tool.callable_function(input_data)
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        call_id = tool_log_repository.create_tool_call_log(
            tool_name=tool_name,
            input_data=input_data,
            output_data=result,
            status="success",
            error_message=None,
            latency_ms=latency_ms,
            user_id=user_id,
        )

        return {
            "tool_name": tool_name,
            "success": True,
            "result": result,
            "error": None,
            "message": "工具调用成功",
            "call_id": call_id,
        }

    except AppError as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        call_id = tool_log_repository.create_tool_call_log(
            tool_name=tool_name,
            input_data=input_data,
            output_data=None,
            status="failed",
            error_message=exc.message,
            latency_ms=latency_ms,
            user_id=user_id,
        )

        raise AppError(
            error=exc.error,
            message=exc.message,
            status_code=exc.status_code,
            call_id=call_id,
            **exc.details,
        )
