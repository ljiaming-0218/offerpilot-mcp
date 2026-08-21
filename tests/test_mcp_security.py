import unittest
import asyncio
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.mcp_security import McpSecurityMiddleware, SlidingWindowRateLimiter
from backend import mcp_server
from backend.tools import registry
from backend.tools.base import ToolDefinition


async def endpoint(request):
    return JSONResponse({"status": "ok"})


def build_client(token: str = "test-mcp-token", limit: int = 10) -> TestClient:
    app = Starlette(routes=[Route("/", endpoint, methods=["POST"])])
    protected_app = McpSecurityMiddleware(
        app,
        access_token=token,
        rate_limit_requests=limit,
        rate_limit_window_seconds=60,
    )
    return TestClient(protected_app)


class McpSecurityMiddlewareTests(unittest.TestCase):
    def test_missing_token_is_rejected(self) -> None:
        response = build_client().post("/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "INVALID_MCP_TOKEN")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_invalid_token_is_rejected(self) -> None:
        response = build_client().post(
            "/",
            headers={"Authorization": "Bearer wrong-token"},
        )

        self.assertEqual(response.status_code, 401)

    def test_valid_token_reaches_mcp_application(self) -> None:
        response = build_client().post(
            "/",
            headers={"Authorization": "Bearer test-mcp-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_missing_server_configuration_fails_closed(self) -> None:
        response = build_client(token="").post(
            "/",
            headers={"Authorization": "Bearer any-token"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "MCP_AUTH_NOT_CONFIGURED")

    def test_rate_limit_returns_retry_after(self) -> None:
        client = build_client(limit=2)
        headers = {"Authorization": "Bearer test-mcp-token"}

        self.assertEqual(client.post("/", headers=headers).status_code, 200)
        self.assertEqual(client.post("/", headers=headers).status_code, 200)
        response = client.post("/", headers=headers)

        self.assertEqual(response.status_code, 429)
        self.assertIn("retry-after", response.headers)


class SlidingWindowRateLimiterTests(unittest.TestCase):
    def test_expired_requests_leave_window(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)

        self.assertEqual(limiter.check("client", now=0), (True, 0))
        self.assertEqual(limiter.check("client", now=1)[0], False)
        self.assertEqual(limiter.check("client", now=11), (True, 0))


class McpToolAuditTests(unittest.TestCase):
    def test_skill_catalog_resource_uses_real_skill_registry(self) -> None:
        with patch(
            "backend.mcp_server.registry.call_tool",
            return_value={"result": [{"skill_name": "Python", "job_count": 2}]},
        ) as call_tool:
            resource = mcp_server.skill_catalog()

        self.assertEqual(resource["skills"][0]["skill_name"], "Python")
        self.assertEqual(
            call_tool.call_args.args,
            ("list_skills", {}),
        )
        self.assertEqual(call_tool.call_args.kwargs["user_id"], "mcp_resource")

    def test_skill_catalog_is_advertised_as_mcp_resource(self) -> None:
        resources = asyncio.run(mcp_server.offerpilot_mcp.list_resources())

        self.assertTrue(
            any(str(resource.uri) == "offerpilot://skills/catalog" for resource in resources)
        )

    def test_mcp_prompts_are_advertised(self) -> None:
        prompts = asyncio.run(mcp_server.offerpilot_mcp.list_prompts())
        prompt_names = {prompt.name for prompt in prompts}

        self.assertIn("job_interview_prompt", prompt_names)
        self.assertIn("skill_gap_study_plan_prompt", prompt_names)

    def test_search_jobs_passes_filters_and_pagination_to_registry(self) -> None:
        with patch(
            "backend.mcp_server.registry.call_tool",
            return_value={
                "result": {
                    "jobs": [],
                    "returned": 0,
                    "limit": 25,
                    "offset": 50,
                    "has_more": False,
                    "filters": {"city": "上海"},
                }
            },
        ) as call_tool:
            result = mcp_server.search_jobs(
                keyword="Agent",
                city="上海",
                job_type="实习",
                skill="RAG",
                extraction_status="completed",
                limit=25,
                offset=50,
            )

        self.assertEqual(result["limit"], 25)
        self.assertEqual(
            call_tool.call_args.args,
            (
                "search_jobs",
                {
                    "keyword": "Agent",
                    "city": "上海",
                    "job_type": "实习",
                    "skill": "RAG",
                    "extraction_status": "completed",
                    "limit": 25,
                    "offset": 50,
                },
            ),
        )
        self.assertEqual(call_tool.call_args.kwargs["user_id"], "mcp")

    def test_job_detail_tools_call_registry_as_mcp_user(self) -> None:
        with patch(
            "backend.mcp_server.registry.call_tool",
            return_value={"result": {"job_id": 7}},
        ) as call_tool:
            detail = mcp_server.get_job_detail(7)
            requirements = mcp_server.get_job_requirements(7)

        self.assertEqual(detail["job_id"], 7)
        self.assertEqual(requirements["job_id"], 7)
        self.assertEqual(
            call_tool.call_args_list[0].args,
            ("get_job_detail", {"job_id": 7}),
        )
        self.assertEqual(call_tool.call_args_list[0].kwargs["user_id"], "mcp")
        self.assertEqual(
            call_tool.call_args_list[1].args,
            ("get_job_requirements", {"job_id": 7}),
        )

    def test_tool_log_records_mcp_source(self) -> None:
        tool = ToolDefinition(
            tool_name="audit_test",
            description="audit test",
            risk_level="low",
            enabled=True,
            callable_function=lambda input_data: {"value": input_data["value"]},
        )

        with (
            patch.dict(registry.TOOLS, {"audit_test": tool}, clear=True),
            patch(
                "backend.tools.registry.tool_log_repository.create_tool_call_log",
                return_value=9,
            ) as create_log,
        ):
            result = registry.call_tool("audit_test", {"value": 1}, user_id="mcp")

        self.assertTrue(result["success"])
        self.assertEqual(result["call_id"], 9)
        self.assertEqual(create_log.call_args.kwargs["user_id"], "mcp")


if __name__ == "__main__":
    unittest.main()
