import json
import re

from backend.repositories import agent_trace_repository
from backend.agent import intent_router, planner, skill_loader
from backend.errors import AppError
from backend.tools import registry


def run_agent(task: str, user_id: str | None = None) -> dict:
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
            "generation_mode": route_result["generation_mode"],
            "confidence": route_result["confidence"],
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

    allowed_tools = set(skill["allowed_tools"])
    if not allowed_tools:
        raise AppError(
            error="SKILL_TOOLS_NOT_CONFIGURED",
            message="Skill 未配置可调用工具，已停止执行",
            status_code=500,
            skill_name=skill_name,
        )

    trace.append(
        {
            "step": 2,
            "type": "skill",
            "content": f"加载 {skill_name} Skill，并应用工具权限约束",
            "skill_name": skill_name,
            "allowed_tools": sorted(allowed_tools),
            "execution_steps": skill["execution_steps"],
        }
    )

    plan = planner.create_plan(task, skill_name, allowed_tools)
    trace.append(
        {
            "step": len(trace) + 1,
            "type": "plan",
            "content": f"生成 {len(plan['steps'])} 步受控执行计划",
            "reason": plan["reason"],
            "generation_mode": plan["generation_mode"],
            "confidence": plan["confidence"],
            "execution_steps": [
                f"{item['tool_name']}：{item['reason']}" for item in plan["steps"]
            ],
        }
    )

    tool_outputs = _execute_plan(
        task=task,
        plan_steps=plan["steps"],
        trace=trace,
        allowed_tools=allowed_tools,
        user_id=user_id,
    )
    final_answer = _build_final_answer(skill_name, tool_outputs)
    return _finalize_agent_result(
        task=task,
        skill_name=skill_name,
        trace=trace,
        final_answer=final_answer,
        user_id=user_id,
    )


def _execute_plan(
    task: str,
    plan_steps: list[dict],
    trace: list[dict],
    allowed_tools: set[str],
    user_id: str | None,
) -> dict[str, dict]:
    if len(plan_steps) > planner.MAX_PLAN_STEPS:
        raise AppError(
            error="AGENT_MAX_STEPS_EXCEEDED",
            message="Agent 执行计划超过最大步数",
            status_code=400,
            max_steps=planner.MAX_PLAN_STEPS,
        )

    tool_outputs = {}
    executed_calls = set()
    for plan_step in plan_steps:
        tool_name = plan_step["tool_name"]
        tool_input = _build_tool_input(tool_name, task, tool_outputs)
        call_signature = json.dumps(
            {"tool_name": tool_name, "input": tool_input},
            ensure_ascii=False,
            sort_keys=True,
        )
        if call_signature in executed_calls:
            raise AppError(
                error="AGENT_DUPLICATE_TOOL_CALL",
                message="Agent 检测到重复工具调用，已停止执行",
                status_code=400,
                tool_name=tool_name,
            )
        executed_calls.add(call_signature)

        tool_result = _call_tool_with_trace(
            trace=trace,
            tool_name=tool_name,
            tool_input=tool_input,
            content=f"执行计划：{plan_step['reason']}",
            allowed_tools=allowed_tools,
            user_id=user_id,
        )
        tool_outputs[tool_name] = tool_result["result"]

    return tool_outputs


def _build_tool_input(tool_name: str, task: str, tool_outputs: dict[str, dict]) -> dict:
    if tool_name == "text2sql_query":
        return {"question": task}

    if tool_name == "crawl_job_url":
        url = _extract_url(task)
        if url is None:
            raise AppError(
                error="URL_REQUIRED",
                message="采集任务需要包含公开岗位 URL",
                status_code=400,
            )
        return {"url": url}

    if tool_name == "extract_skills":
        crawl_result = tool_outputs.get("crawl_job_url")
        job_id = crawl_result.get("job_id") if crawl_result else _extract_job_id(task)
        if job_id is None:
            raise AppError(
                error="JOB_ID_REQUIRED",
                message="岗位分析需要明确岗位 ID，或先成功采集岗位",
                status_code=400,
            )
        return {"job_id": job_id}

    raise AppError(
        error="AGENT_TOOL_INPUT_UNSUPPORTED",
        message="Agent 暂不支持构造该工具的输入参数",
        status_code=400,
        tool_name=tool_name,
    )


def _build_final_answer(skill_name: str, tool_outputs: dict[str, dict]) -> str:
    if skill_name == "job-search":
        return _build_job_search_answer(tool_outputs["text2sql_query"])
    if skill_name == "jd-analysis":
        return _build_jd_analysis_answer(tool_outputs["extract_skills"])
    if skill_name == "jd-crawl":
        crawl_answer = _build_jd_crawl_answer(tool_outputs["crawl_job_url"])
        analysis_result = tool_outputs.get("extract_skills")
        if analysis_result is not None:
            return f"{crawl_answer}；{_build_jd_analysis_answer(analysis_result)}"
        return crawl_answer
    raise AppError(
        error="SKILL_NOT_SUPPORTED",
        message="当前 Agent Executor 暂不支持该 Skill 的结果汇总",
        status_code=400,
        skill_name=skill_name,
    )


def _build_job_search_answer(tool_result: dict) -> str:
    rows = tool_result.get("rows", [])
    sql = tool_result.get("sql", "")
    generation_mode = tool_result.get("generation_mode", "unknown")
    mode_labels = {
        "llm": "大模型生成",
        "llm_repaired": "大模型自修复",
        "rules_fallback": "规则兜底",
    }
    mode_text = mode_labels.get(generation_mode, "未知方式")

    if not rows:
        return f"已通过{mode_text}生成并执行安全查询，但没有找到匹配岗位。生成 SQL：{sql}"

    return f"已通过{mode_text}生成并执行安全查询，找到 {len(rows)} 条匹配结果。生成 SQL：{sql}"


def _call_tool_with_trace(
    trace: list[dict],
    tool_name: str,
    tool_input: dict,
    content: str,
    allowed_tools: set[str],
    user_id: str | None = None,
) -> dict:
    if tool_name not in allowed_tools:
        raise AppError(
            error="TOOL_NOT_ALLOWED_BY_SKILL",
            message="当前 Skill 不允许调用该工具",
            status_code=403,
            tool_name=tool_name,
            allowed_tools=sorted(allowed_tools),
        )

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

    tool_result = registry.call_tool(tool_name, tool_input, user_id=user_id)

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
    user_id: str | None = None,
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
        user_id=user_id,
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
    patterns = [
        r"(?:岗位|job)\s*(?:id\s*[=:：]?\s*)?(\d+)",
        r"(\d+)\s*号岗位",
        r"(?:分析|解析|提取)\s*(\d+)\s*(?:号)?(?:岗位)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, task, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


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
