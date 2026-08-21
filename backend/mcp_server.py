from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from backend.config import settings
from backend.mcp_security import McpSecurityMiddleware
from backend.tools import registry


offerpilot_mcp = MCPServer(
    name="offerpilot-mcp",
    title="OfferPilot MCP",
    description="查询真实岗位与技能数据的 OfferPilot MCP Server",
    instructions=(
        "只根据 OfferPilot 数据库中的真实岗位信息回答。"
        "岗位自然语言查询必须通过 text2sql_query 的 SQL Guard。"
    ),
    version="0.1.0",
)


READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


@offerpilot_mcp.resource(
    "offerpilot://skills/catalog",
    name="OfferPilot 技能目录",
    title="真实岗位技能目录",
    description="从 OfferPilot 真实岗位数据中读取技能名称、分类和关联岗位数量。",
    mime_type="application/json",
)
def skill_catalog() -> dict[str, Any]:
    skills = registry.call_tool("list_skills", {}, user_id="mcp_resource")["result"]
    return {
        "source": "OfferPilot MySQL skills/job_skills",
        "skills": skills,
    }


@offerpilot_mcp.tool(
    name="search_jobs",
    title="查询岗位列表",
    description="分页读取 OfferPilot 数据库中的真实岗位列表，可按关键词、城市、岗位类型、技能和抽取状态筛选。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def search_jobs(
    keyword: str | None = None,
    city: str | None = None,
    job_type: str | None = None,
    skill: str | None = None,
    extraction_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    return registry.call_tool(
        "search_jobs",
        {
            "keyword": keyword,
            "city": city,
            "job_type": job_type,
            "skill": skill,
            "extraction_status": extraction_status,
            "limit": limit,
            "offset": offset,
        },
        user_id="mcp",
    )["result"]


@offerpilot_mcp.tool(
    name="get_job_detail",
    title="查看岗位详情",
    description="按岗位 ID 读取真实岗位的公司、地点、岗位描述和来源链接。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def get_job_detail(job_id: int) -> dict[str, Any]:
    return registry.call_tool(
        "get_job_detail", {"job_id": job_id}, user_id="mcp"
    )["result"]


@offerpilot_mcp.tool(
    name="get_job_requirements",
    title="查看岗位要求",
    description="按岗位 ID 读取已从真实 JD 验证的技能、学历、英语、专业和经验要求。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def get_job_requirements(job_id: int) -> dict[str, Any]:
    return registry.call_tool(
        "get_job_requirements", {"job_id": job_id}, user_id="mcp"
    )["result"]


@offerpilot_mcp.tool(
    name="list_skills",
    title="查询技能统计",
    description="读取真实岗位关联的技能及岗位数量统计。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def list_skills() -> list[dict[str, Any]]:
    return registry.call_tool("list_skills", {}, user_id="mcp")["result"]


@offerpilot_mcp.tool(
    name="text2sql_query",
    title="自然语言查询岗位",
    description="将受支持的中文岗位问题转换为只读 SQL，经 SQL Guard 后查询真实数据库。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def text2sql_query(question: str) -> dict[str, Any]:
    return registry.call_tool("text2sql_query", {"question": question}, user_id="mcp")["result"]


@offerpilot_mcp.prompt(
    name="job_interview_prompt",
    title="基于岗位生成面试问题",
    description="引导 MCP Host 读取真实岗位详情和要求，再生成可追溯的模拟面试问题。",
)
def job_interview_prompt(job_id: int, candidate_focus: str | None = None) -> str:
    focus_text = f"候选人重点背景：{candidate_focus}\n" if candidate_focus else ""
    return (
        "你是 OfferPilot 的模拟面试官。请只基于 OfferPilot MCP 工具读取到的真实岗位信息出题，"
        "不要编造岗位要求或公司信息。\n"
        f"岗位 ID：{job_id}\n"
        f"{focus_text}"
        "执行步骤：\n"
        "1. 调用 get_job_detail 读取岗位标题、公司、城市、描述和来源链接。\n"
        "2. 调用 get_job_requirements 读取已验证的技能、学历、英语、专业和经验要求。\n"
        "3. 生成 3 道中文面试题，覆盖项目追问、原理理解和工程实践。\n"
        "4. 每道题必须包含：问题、命中考点、出题依据、参考回答要点。\n"
        "5. 如果岗位要求为空，请明确说明数据不足，并建议先补做岗位要求抽取。"
    )


@offerpilot_mcp.prompt(
    name="skill_gap_study_plan_prompt",
    title="基于岗位缺口生成学习计划",
    description="引导 MCP Host 用真实岗位和技能目录分析技能补齐优先级。",
)
def skill_gap_study_plan_prompt(
    target_role: str | None = None,
    city: str | None = None,
    skill: str | None = None,
) -> str:
    filters = []
    if target_role:
        filters.append(f"目标岗位关键词：{target_role}")
    if city:
        filters.append(f"目标城市：{city}")
    if skill:
        filters.append(f"关注技能：{skill}")
    filter_text = "\n".join(filters) or "无额外筛选条件"

    return (
        "你是 OfferPilot 的学习计划助手。请基于 OfferPilot MCP 的真实岗位数据和技能目录，"
        "给出技能补齐建议；不要编造课程、证书、学习时长或就业结果。\n"
        f"筛选条件：\n{filter_text}\n"
        "执行步骤：\n"
        "1. 调用 search_jobs，使用分页和筛选参数读取相关岗位，单次 limit 不超过 20。\n"
        "2. 调用 list_skills 读取真实技能统计。\n"
        "3. 对代表性岗位调用 get_job_requirements，确认技能、学历、英语、专业和经验要求。\n"
        "4. 按岗位出现频次和要求强度输出 3-5 个优先补齐方向。\n"
        "5. 每个方向必须包含：技能或要求、关联岗位依据、为什么优先、下一步行动建议。"
    )


def _transport_security() -> TransportSecuritySettings | None:
    allowed_hosts = settings.mcp_allowed_host_list
    if not allowed_hosts:
        return None

    return TransportSecuritySettings(
        allowed_hosts=allowed_hosts,
        allowed_origins=settings.mcp_allowed_origin_list,
    )


mcp_transport_app = offerpilot_mcp.streamable_http_app(
    streamable_http_path="/",
    transport_security=_transport_security(),
)

mcp_http_app = McpSecurityMiddleware(
    mcp_transport_app,
    access_token=settings.mcp_access_token,
    rate_limit_requests=settings.mcp_rate_limit_requests,
    rate_limit_window_seconds=settings.mcp_rate_limit_window_seconds,
)
