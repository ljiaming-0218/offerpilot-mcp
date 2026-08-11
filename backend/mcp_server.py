from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from backend.config import settings
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
    return registry.call_tool("search_jobs", {})["result"]


@offerpilot_mcp.tool(
    name="list_skills",
    title="查询技能统计",
    description="读取真实岗位关联的技能及岗位数量统计。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def list_skills() -> list[dict[str, Any]]:
    return registry.call_tool("list_skills", {})["result"]


@offerpilot_mcp.tool(
    name="text2sql_query",
    title="自然语言查询岗位",
    description="将受支持的中文岗位问题转换为只读 SQL，经 SQL Guard 后查询真实数据库。",
    annotations=READ_ONLY_TOOL,
    structured_output=True,
)
def text2sql_query(question: str) -> dict[str, Any]:
    return registry.call_tool("text2sql_query", {"question": question})["result"]


def _transport_security() -> TransportSecuritySettings | None:
    allowed_hosts = settings.mcp_allowed_host_list
    if not allowed_hosts:
        return None

    return TransportSecuritySettings(
        allowed_hosts=allowed_hosts,
        allowed_origins=settings.mcp_allowed_origin_list,
    )


mcp_http_app = offerpilot_mcp.streamable_http_app(
    streamable_http_path="/",
    transport_security=_transport_security(),
)
