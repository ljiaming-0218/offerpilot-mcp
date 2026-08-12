import unittest
from unittest.mock import patch

from backend.agent import executor, intent_router, planner, skill_loader
from backend.errors import AppError


class AgentRouterTests(unittest.TestCase):
    def test_uses_valid_llm_route(self) -> None:
        with (
            patch("backend.agent.intent_router.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.agent.intent_router.llm_service.chat_json",
                return_value={
                    "skill_name": "job-search",
                    "reason": "用户需要查询已有岗位数据",
                    "confidence": 0.92,
                },
            ),
        ):
            result = intent_router.route_task("北京有哪些 Agent 岗位？")

        self.assertEqual(result["skill_name"], "job-search")
        self.assertEqual(result["generation_mode"], "llm")
        self.assertEqual(result["confidence"], 0.92)

    def test_invalid_llm_skill_falls_back_to_rules(self) -> None:
        with (
            patch("backend.agent.intent_router.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.agent.intent_router.llm_service.chat_json",
                return_value={
                    "skill_name": "delete-database",
                    "reason": "invalid",
                    "confidence": 0.99,
                },
            ),
        ):
            result = intent_router.route_task("分析 21 号岗位")

        self.assertEqual(result["skill_name"], "jd-analysis")
        self.assertEqual(result["generation_mode"], "rules_fallback")

    def test_crawl_route_requires_url_in_task(self) -> None:
        with (
            patch("backend.agent.intent_router.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.agent.intent_router.llm_service.chat_json",
                return_value={
                    "skill_name": "jd-crawl",
                    "reason": "用户想采集岗位",
                    "confidence": 0.9,
                },
            ),
        ):
            result = intent_router.route_task("帮我采集一个岗位")

        self.assertEqual(result["skill_name"], "job-search")

    def test_low_confidence_llm_route_falls_back_to_rules(self) -> None:
        with (
            patch("backend.agent.intent_router.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.agent.intent_router.llm_service.chat_json",
                return_value={
                    "skill_name": "jd-analysis",
                    "reason": "不确定是否需要分析",
                    "confidence": 0.3,
                },
            ),
        ):
            result = intent_router.route_task("分析 21 号岗位")

        self.assertEqual(result["skill_name"], "jd-analysis")
        self.assertEqual(result["generation_mode"], "rules_fallback")

    def test_company_top_five_is_not_mistaken_for_job_id(self) -> None:
        with patch(
            "backend.agent.intent_router.llm_service.is_llm_available",
            return_value=False,
        ):
            result = intent_router.route_task("查询岗位数最多的前5家公司")

        self.assertEqual(result["skill_name"], "job-search")

    def test_rules_route_profile_match_and_mock_interview(self) -> None:
        with patch(
            "backend.agent.intent_router.llm_service.is_llm_available",
            return_value=False,
        ):
            match_result = intent_router.route_task("根据我的简历匹配岗位")
            interview_result = intent_router.route_task("针对 21 号岗位进行模拟面试")

        self.assertEqual(match_result["skill_name"], "profile-match")
        self.assertEqual(interview_result["skill_name"], "mock-interview")


class SkillLoaderTests(unittest.TestCase):
    def test_loads_structured_job_search_constraints(self) -> None:
        skill = skill_loader.load_skill("job-search")

        self.assertIsNotNone(skill)
        self.assertIn("text2sql_query", skill["allowed_tools"])
        self.assertGreaterEqual(len(skill["execution_steps"]), 3)
        self.assertGreaterEqual(len(skill["quality_checks"]), 2)

    def test_crawl_skill_allows_conditional_analysis(self) -> None:
        skill = skill_loader.load_skill("jd-crawl")

        self.assertIsNotNone(skill)
        self.assertEqual(skill["allowed_tools"], ["crawl_job_url", "extract_skills"])

    def test_profile_and_interview_skills_have_single_purpose_tools(self) -> None:
        profile_skill = skill_loader.load_skill("profile-match")
        interview_skill = skill_loader.load_skill("mock-interview")

        self.assertEqual(profile_skill["allowed_tools"], ["match_my_profile"])
        self.assertEqual(interview_skill["allowed_tools"], ["generate_my_mock_interview"])


class AgentPlannerTests(unittest.TestCase):
    def test_rules_plan_adds_analysis_after_crawl_when_requested(self) -> None:
        plan = planner._create_rules_plan(
            "采集 https://example.com/jobs/1 并分析岗位要求",
            "jd-crawl",
            {"crawl_job_url", "extract_skills"},
        )

        self.assertEqual(plan["generation_mode"], "rules_fallback")
        self.assertEqual(
            [step["tool_name"] for step in plan["steps"]],
            ["crawl_job_url", "extract_skills"],
        )

    def test_llm_plan_rejects_cross_skill_tool(self) -> None:
        plan = planner._normalize_llm_plan(
            "查询北京岗位",
            "job-search",
            {"text2sql_query"},
            {
                "reason": "先采集再查询",
                "confidence": 0.9,
                "steps": [{"tool_name": "crawl_job_url", "reason": "不应调用"}],
            },
        )

        self.assertIsNone(plan)

    def test_llm_plan_rejects_wrong_crawl_shape(self) -> None:
        plan = planner._normalize_llm_plan(
            "采集 https://example.com/jobs/1 并分析岗位要求",
            "jd-crawl",
            {"crawl_job_url", "extract_skills"},
            {
                "reason": "遗漏采集步骤",
                "confidence": 0.9,
                "steps": [{"tool_name": "extract_skills", "reason": "不应先分析"}],
            },
        )

        self.assertIsNone(plan)

    def test_rules_plan_for_profile_and_interview_is_single_step(self) -> None:
        profile_plan = planner._create_rules_plan(
            "根据我的简历匹配岗位",
            "profile-match",
            {"match_my_profile"},
        )
        interview_plan = planner._create_rules_plan(
            "针对 21 号岗位进行模拟面试",
            "mock-interview",
            {"generate_my_mock_interview"},
        )

        self.assertEqual(profile_plan["steps"][0]["tool_name"], "match_my_profile")
        self.assertEqual(
            interview_plan["steps"][0]["tool_name"],
            "generate_my_mock_interview",
        )


class AgentExecutorPermissionTests(unittest.TestCase):
    def test_rejects_tool_outside_skill_whitelist(self) -> None:
        trace = []
        with (
            patch("backend.agent.executor.registry.call_tool") as call_tool,
            self.assertRaises(AppError) as context,
        ):
            executor._call_tool_with_trace(
                trace=trace,
                tool_name="crawl_job_url",
                tool_input={"url": "https://example.com/job"},
                content="test",
                allowed_tools={"text2sql_query"},
            )

        self.assertEqual(context.exception.error, "TOOL_NOT_ALLOWED_BY_SKILL")
        call_tool.assert_not_called()

    def test_calls_tool_inside_skill_whitelist(self) -> None:
        trace = []
        with patch(
            "backend.agent.executor.registry.call_tool",
            return_value={"result": {"rows": []}, "call_id": 7},
        ) as call_tool:
            result = executor._call_tool_with_trace(
                trace=trace,
                tool_name="text2sql_query",
                tool_input={"question": "北京岗位"},
                content="test",
                allowed_tools={"text2sql_query"},
            )

        self.assertEqual(result["call_id"], 7)
        self.assertEqual(len(trace), 2)
        call_tool.assert_called_once()

    def test_two_step_plan_uses_crawl_job_id_for_skill_extraction(self) -> None:
        trace = []
        steps = [
            {"tool_name": "crawl_job_url", "reason": "采集岗位"},
            {"tool_name": "extract_skills", "reason": "分析岗位"},
        ]
        with patch(
            "backend.agent.executor.registry.call_tool",
            side_effect=[
                {"result": {"job_id": 88, "message": "采集完成"}, "call_id": 10},
                {"result": {"skills": [{"skill_name": "Python"}]}, "call_id": 11},
            ],
        ) as call_tool:
            outputs = executor._execute_plan(
                task="采集 https://example.com/jobs/1 并分析岗位要求",
                plan_steps=steps,
                trace=trace,
                allowed_tools={"crawl_job_url", "extract_skills"},
                user_id="admin-1",
                current_user={"user_id": "admin-1", "role": "admin"},
            )

        self.assertEqual(outputs["crawl_job_url"]["job_id"], 88)
        self.assertEqual(outputs["extract_skills"]["skills"][0]["skill_name"], "Python")
        self.assertEqual(call_tool.call_args_list[0].args, ("crawl_job_url", {"url": "https://example.com/jobs/1"}))
        self.assertEqual(call_tool.call_args_list[0].kwargs["user_id"], "admin-1")
        self.assertEqual(call_tool.call_args_list[1].args, ("extract_skills", {"job_id": 88}))
        self.assertEqual(len(trace), 4)

    def test_profile_tools_receive_trusted_execution_context(self) -> None:
        trace = []
        with patch(
            "backend.agent.executor.registry.call_tool",
            return_value={"result": {"matches": []}, "call_id": 12},
        ) as call_tool:
            executor._execute_plan(
                task="根据我的简历匹配岗位",
                plan_steps=[{"tool_name": "match_my_profile", "reason": "匹配岗位"}],
                trace=trace,
                allowed_tools={"match_my_profile"},
                user_id="3",
                current_user={"user_id": 3, "role": "user"},
            )

        self.assertEqual(call_tool.call_args.args, ("match_my_profile", {}))
        self.assertEqual(
            call_tool.call_args.kwargs["execution_context"],
            {"current_user": {"user_id": 3, "role": "user"}},
        )


if __name__ == "__main__":
    unittest.main()
