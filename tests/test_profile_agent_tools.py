import unittest
from unittest.mock import patch

from backend.errors import AppError
from backend.tools import profile_tools
from backend.services import study_plan_service
from backend.routers import profile_router
from backend.schemas.user_profile_schema import StudyPlanResult


class ProfileAgentToolTests(unittest.TestCase):
    def test_match_tool_requires_trusted_context(self) -> None:
        with self.assertRaises(AppError) as context:
            profile_tools.match_my_profile({})

        self.assertEqual(context.exception.error, "TOOL_CONTEXT_REQUIRED")

    def test_match_tool_uses_profile_owned_by_current_user(self) -> None:
        current_user = {"user_id": 7, "role": "user"}
        profile = {"user_id": "resume-7", "owner_user_id": 7}
        with (
            patch(
                "backend.tools.profile_tools.profile_match_service.list_user_profiles",
                return_value=[profile],
            ) as list_profiles,
            patch(
                "backend.tools.profile_tools.profile_match_service.match_jobs_for_user",
                return_value={"matches": []},
            ) as match_jobs,
        ):
            result = profile_tools.match_my_profile(
                {"_execution_context": {"current_user": current_user}}
            )

        self.assertEqual(result, {"matches": []})
        list_profiles.assert_called_once_with(current_user)
        match_jobs.assert_called_once_with("resume-7", current_user=current_user)

    def test_interview_tool_uses_profile_owned_by_current_user(self) -> None:
        current_user = {"user_id": 7, "role": "user"}
        profile = {"user_id": "resume-7", "owner_user_id": 7}
        with (
            patch(
                "backend.tools.profile_tools.profile_match_service.list_user_profiles",
                return_value=[profile],
            ),
            patch(
                "backend.tools.profile_tools.interview_service.generate_mock_interview",
                return_value={"session_id": 5},
            ) as generate_interview,
        ):
            result = profile_tools.generate_my_mock_interview(
                {
                    "job_id": 21,
                    "_execution_context": {"current_user": current_user},
                }
            )

        self.assertEqual(result, {"session_id": 5})
        payload = generate_interview.call_args.args[0]
        self.assertEqual(payload.user_id, "resume-7")
        self.assertEqual(payload.job_id, 21)
        self.assertEqual(generate_interview.call_args.kwargs["current_user"], current_user)

    def test_answer_evaluation_tool_validates_with_current_user(self) -> None:
        current_user = {"user_id": 7, "role": "user"}
        profile = {"user_id": "resume-7", "owner_user_id": 7}
        with (
            patch(
                "backend.tools.profile_tools.profile_match_service.list_user_profiles",
                return_value=[profile],
            ),
            patch(
                "backend.tools.profile_tools.interview_service.evaluate_answer",
                return_value={"score": 80},
            ) as evaluate_answer,
        ):
            result = profile_tools.evaluate_my_interview_answer(
                {
                    "payload": {
                        "session_id": 5,
                        "question": "请介绍项目架构",
                        "user_answer": "我先说明数据流，再说明服务边界和测试方法。",
                    },
                    "_execution_context": {"current_user": current_user},
                }
            )

        self.assertEqual(result, {"score": 80})
        self.assertEqual(evaluate_answer.call_args.args[0].session_id, 5)
        self.assertEqual(evaluate_answer.call_args.kwargs["current_user"], current_user)


class StudyPlanServiceTests(unittest.TestCase):
    def test_study_plan_orders_skills_by_real_missing_job_counts(self) -> None:
        current_user = {"user_id": 7, "role": "user"}
        profile = {"user_id": "resume-7", "owner_user_id": 7}
        matches = {
            "total_jobs": 3,
            "matched_jobs": 2,
            "matches": [
                {"company_name": "公司A", "title": "岗位A", "missing_skills": ["RAG", "Python"]},
                {"company_name": "公司B", "title": "岗位B", "missing_skills": ["RAG", "Agent"]},
                {"company_name": "公司C", "title": "岗位C", "missing_skills": ["RAG"]},
            ],
        }
        with (
            patch(
                "backend.services.study_plan_service.profile_match_service.list_user_profiles",
                return_value=[profile],
            ),
            patch(
                "backend.services.study_plan_service.profile_match_service.match_jobs_for_user",
                return_value=matches,
            ),
        ):
            result = study_plan_service.generate_study_plan_for_current_user(current_user)

        self.assertEqual(result["focus_skills"], ["RAG", "Python", "Agent"])
        self.assertEqual(result["plan_items"][0]["target_job_count"], 3)
        self.assertEqual(result["plan_items"][0]["matched_job_examples"], ["公司A·岗位A", "公司B·岗位B"])

    def test_study_plan_route_uses_current_login_identity(self) -> None:
        current_user = {"user_id": 7, "role": "user"}
        payload = {
            "user_id": "resume-7",
            "total_jobs": 3,
            "matched_jobs": 2,
            "focus_skills": ["RAG"],
            "plan_items": [
                {
                    "priority": 1,
                    "skill_name": "RAG",
                    "target_job_count": 3,
                    "matched_job_examples": ["公司A·岗位A"],
                    "action": "完成一个可展示的 RAG 项目改造。",
                }
            ],
            "message": "已生成学习优先级。",
        }
        with patch(
            "backend.routers.profile_router.study_plan_service.generate_study_plan_for_current_user",
            return_value=payload,
        ) as generate_plan:
            result = profile_router.generate_study_plan(current_user=current_user)

        validated = StudyPlanResult(**result)
        self.assertEqual(validated.plan_items[0].skill_name, "RAG")
        generate_plan.assert_called_once_with(current_user)


if __name__ == "__main__":
    unittest.main()
