
import time

from backend.errors import AppError
from backend.repositories import tool_log_repository

from backend.tools.base import ToolDefinition
from backend.tools.crawler_tools import crawl_job_url
from backend.tools.job_tools import extract_skills, search_jobs
from backend.tools.profile_tools import (
    evaluate_my_interview_answer,
    generate_my_mock_interview,
    generate_my_study_plan,
    match_my_profile,
)
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
    "match_my_profile": ToolDefinition(
        tool_name="match_my_profile",
        description="使用当前登录用户最近更新的画像匹配真实岗位",
        risk_level="medium",
        enabled=True,
        callable_function=match_my_profile,
    ),
    "generate_my_mock_interview": ToolDefinition(
        tool_name="generate_my_mock_interview",
        description="基于当前登录用户画像和指定岗位生成模拟面试题",
        risk_level="medium",
        enabled=True,
        callable_function=generate_my_mock_interview,
    ),
    "evaluate_my_interview_answer": ToolDefinition(
        tool_name="evaluate_my_interview_answer",
        description="评估当前登录用户自己的模拟面试回答",
        risk_level="medium",
        enabled=True,
        callable_function=evaluate_my_interview_answer,
    ),
    "generate_my_study_plan": ToolDefinition(
        tool_name="generate_my_study_plan",
        description="根据当前登录用户画像和真实岗位缺口生成学习计划",
        risk_level="medium",
        enabled=True,
        callable_function=generate_my_study_plan,
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


def call_tool(
    tool_name: str,
    input_data: dict,
    user_id: str | None = None,
    execution_context: dict | None = None,
) -> dict:
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

    sanitized_input = {
        key: value
        for key, value in input_data.items()
        if key != "_execution_context"
    }
    execution_input = dict(sanitized_input)
    if execution_context:
        execution_input["_execution_context"] = execution_context

    try:
        result = tool.callable_function(execution_input)
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        call_id = tool_log_repository.create_tool_call_log(
            tool_name=tool_name,
            input_data=sanitized_input,
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
            input_data=sanitized_input,
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
