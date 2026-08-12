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


@offerpilot_mcp.tool(
    name="search_jobs",
    title="查询岗位列表",
    description="读取 OfferPilot 数据库中的真实岗位列表。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def search_jobs() -> list[dict[str, Any]]:
    return registry.call_tool("search_jobs", {}, user_id="mcp")["result"]


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
