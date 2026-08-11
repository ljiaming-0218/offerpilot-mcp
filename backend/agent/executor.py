import re

from backend.repositories import agent_trace_repository
from backend.agent import intent_router, skill_loader
from backend.errors import AppError
from backend.tools import registry


def run_agent(task: str) -> dict:
    trace = []

    route_result = intent_router.route_task(task)
    skill_name = route_result["skill_name"]

    trace.append(
        {
            "step": 1,
            "type": "intent",
            "content": f"识别任务为 {skill_name}",
            "reason": route_result["reason"],
            "skill_name": skill_name,
        }
    )

    skill = skill_loader.load_skill(skill_name)
    if skill is None:
        raise AppError(
            error="SKILL_NOT_FOUND",
            message="未找到对应 Skill",
            status_code=404,
            skill_name=skill_name,
        )

    trace.append(
        {
            "step": 2,
            "type": "skill",
            "content": f"加载 {skill_name} Skill",
            "skill_name": skill_name,
        }
    )

    if skill_name == "job-search":
        tool_result = _call_tool_with_trace(
            trace=trace,
            tool_name="text2sql_query",
            tool_input={"question": task},
            content="调用 text2sql_query 工具",
        )
        final_answer = _build_job_search_answer(tool_result["result"])
        return _finalize_agent_result(
            task=task,
            skill_name=skill_name,
            trace=trace,
            final_answer=final_answer,
        )

    if skill_name == "jd-crawl":
        url = _extract_url(task)
        if url is None:
            raise AppError(
                error="URL_REQUIRED",
                message="采集任务需要包含公开岗位 URL",
                status_code=400,
            )

        tool_result = _call_tool_with_trace(
            trace=trace,
            tool_name="crawl_job_url",
            tool_input={"url": url},
            content="调用 crawl_job_url 工具",
        )
        final_answer = _build_jd_crawl_answer(tool_result["result"])
        return _finalize_agent_result(
            task=task,
            skill_name=skill_name,
            trace=trace,
            final_answer=final_answer,
        )

    if skill_name == "jd-analysis":
        job_id = _extract_job_id(task)
        if job_id is None:
            raise AppError(
                error="JOB_ID_REQUIRED",
                message="岗位分析任务需要包含岗位 ID，例如：分析 24 号岗位",
                status_code=400,
            )

        tool_result = _call_tool_with_trace(
            trace=trace,
            tool_name="extract_skills",
            tool_input={"job_id": job_id},
            content="调用 extract_skills 工具",
        )
        final_answer = _build_jd_analysis_answer(tool_result["result"])
        return _finalize_agent_result(
            task=task,
            skill_name=skill_name,
            trace=trace,
            final_answer=final_answer,
        )


    raise AppError(
        error="SKILL_NOT_SUPPORTED",
        message="当前 Agent Executor 暂不支持该 Skill 的自动执行",
        status_code=400,
        skill_name=skill_name,
    )


def _build_job_search_answer(tool_result: dict) -> str:
    rows = tool_result.get("rows", [])
    sql = tool_result.get("sql", "")

    if not rows:
        return f"已执行安全查询，但没有找到匹配岗位。生成 SQL：{sql}"

    return f"已执行安全查询，找到 {len(rows)} 条匹配结果。生成 SQL：{sql}"


def _call_tool_with_trace(
    trace: list[dict],
    tool_name: str,
    tool_input: dict,
    content: str,
) -> dict:
    next_step = len(trace) + 1
    trace.append(
        {
            "step": next_step,
            "type": "tool_call",
            "content": content,
            "tool_name": tool_name,
            "input": tool_input,
        }
    )

    tool_result = registry.call_tool(tool_name, tool_input)

    trace.append(
        {
            "step": next_step + 1,
            "type": "tool_result",
            "content": f"{tool_name} 工具调用完成",
            "tool_name": tool_name,
            "output": tool_result["result"],
            "call_id": tool_result.get("call_id"),
        }
    )

    return tool_result


def _finalize_agent_result(
    task: str,
    skill_name: str,
    trace: list[dict],
    final_answer: str,
) -> dict:
    trace.append(
        {
            "step": len(trace) + 1,
            "type": "final",
            "content": final_answer,
        }
    )

    trace_id = agent_trace_repository.create_agent_trace(
        task=task,
        skill_name=skill_name,
        trace=trace,
        final_answer=final_answer,
    )

    return {
        "task": task,
        "skill_name": skill_name,
        "final_answer": final_answer,
        "trace": trace,
        "trace_id": trace_id,
    }


def _extract_url(task: str) -> str | None:
    match = re.search(r"https?://[^\s，。]+", task)
    return match.group(0) if match else None


def _extract_job_id(task: str) -> int | None:
    match = re.search(r"(\d+)\s*(号岗位|岗位|job|Job|JOB)?", task)
    return int(match.group(1)) if match else None


def _build_jd_crawl_answer(tool_result: dict) -> str:
    job_id = tool_result.get("job_id")
    message = tool_result.get("message", "岗位采集完成")
    source_url = tool_result.get("source_url", "")
    return f"{message}，job_id={job_id}，source_url={source_url}"


def _build_jd_analysis_answer(tool_result: dict) -> str:
    skills = tool_result.get("skills", [])
    skill_names = "、".join(skill["skill_name"] for skill in skills)
    orientation = tool_result.get("job_orientation", "未知方向")
    difficulty = tool_result.get("difficulty", "unknown")
    return f"岗位技能抽取完成：{skill_names}。岗位方向：{orientation}，难度：{difficulty}。"
