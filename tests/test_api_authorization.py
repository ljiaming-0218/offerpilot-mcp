import unittest
from unittest.mock import patch

from fastapi.routing import APIRoute

from backend.dependencies import get_admin_user, get_current_user
from backend.errors import AppError
from backend.routers.agent_router import router as agent_router
from backend.routers.crawler_router import router as crawler_router
from backend.routers.interview_router import router as interview_router
from backend.routers.job_router import router as job_router
from backend.routers.profile_router import router as profile_router
from backend.routers.skill_router import router as skill_router
from backend.routers.text2sql_router import router as text2sql_router
from backend.routers.tool_router import router as tool_router
from backend.schemas.interview_schema import AnswerEvaluationRequest, MockInterviewRequest
from backend.services import interview_service


class AuthorizationDependencyTests(unittest.TestCase):
    def test_missing_bearer_token_is_rejected(self) -> None:
        with self.assertRaises(AppError) as context:
            get_current_user(None)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.error, "AUTH_REQUIRED")

    def test_non_admin_user_is_rejected(self) -> None:
        with self.assertRaises(AppError) as context:
            get_admin_user({"user_id": 2, "role": "user"})

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.error, "ADMIN_REQUIRED")

    def test_sensitive_routes_use_expected_dependency(self) -> None:
        expected = {
            ("/crawler/fetch-url", "POST"): get_current_user,
            ("/crawler/fetch-urls", "POST"): get_admin_user,
            ("/crawler/import-json", "POST"): get_admin_user,
            ("/crawler/tasks", "GET"): get_admin_user,
            ("/crawler/records", "GET"): get_admin_user,
            ("/jobs", "POST"): get_admin_user,
            ("/jobs", "GET"): get_current_user,
            ("/jobs/{job_id}", "GET"): get_current_user,
            ("/jobs/{job_id}/extract-skills", "POST"): get_admin_user,
            ("/jobs/extract-skills/batch", "POST"): get_admin_user,
            ("/jobs/extract-requirements/batch", "POST"): get_admin_user,
            ("/skills", "GET"): get_current_user,
            ("/skills/workflows", "GET"): get_admin_user,
            ("/query/text2sql", "POST"): get_admin_user,
            ("/tools", "GET"): get_admin_user,
            ("/tools/logs", "GET"): get_admin_user,
            ("/tools/{tool_name}/call", "POST"): get_admin_user,
            ("/agent/route", "POST"): get_admin_user,
            ("/agent/run", "POST"): get_admin_user,
            ("/agent/traces", "GET"): get_admin_user,
            ("/profile/parse-resume", "POST"): get_current_user,
            ("/interview/mock", "POST"): get_current_user,
            ("/interview/evaluate", "POST"): get_current_user,
        }
        routers = [
            crawler_router,
            job_router,
            skill_router,
            text2sql_router,
            tool_router,
            agent_router,
            profile_router,
            interview_router,
        ]
        actual = {}
        for router in routers:
            for route in router.routes:
                if not isinstance(route, APIRoute):
                    continue
                dependencies = {item.call for item in route.dependant.dependencies}
                for method in route.methods:
                    key = (route.path, method)
                    if key in expected:
                        actual[key] = expected[key] in dependencies

        self.assertEqual(set(actual), set(expected))
        self.assertTrue(all(actual.values()))


class InterviewOwnershipTests(unittest.TestCase):
    def test_mock_interview_stops_when_profile_is_not_accessible(self) -> None:
        payload = MockInterviewRequest(user_id="profile-other", job_id=1)
        denied = AppError(error="PROFILE_FORBIDDEN", message="无权访问", status_code=403)

        with (
            patch(
                "backend.services.interview_service.profile_match_service.get_user_profile",
                side_effect=denied,
            ),
            patch("backend.services.interview_service.job_repository.get_job_by_id") as get_job,
        ):
            with self.assertRaises(AppError) as context:
                interview_service.generate_mock_interview(
                    payload,
                    current_user={"user_id": 2, "role": "user"},
                )

        self.assertEqual(context.exception.status_code, 403)
        get_job.assert_not_called()

    def test_answer_evaluation_stops_before_write_for_other_users_session(self) -> None:
        payload = AnswerEvaluationRequest(
            session_id=8,
            question="请说明项目架构",
            user_answer="我会先说明整体数据流，然后解释各层职责和验证方式。",
        )
        denied = AppError(error="PROFILE_FORBIDDEN", message="无权访问", status_code=403)

        with (
            patch(
                "backend.services.interview_service.interview_repository.get_interview_session",
                return_value={"session_id": 8, "user_id": "profile-other", "questions": []},
            ),
            patch(
                "backend.services.interview_service.profile_match_service.get_user_profile",
                side_effect=denied,
            ),
            patch(
                "backend.services.interview_service.interview_repository.create_answer_evaluation"
            ) as create_evaluation,
        ):
            with self.assertRaises(AppError) as context:
                interview_service.evaluate_answer(
                    payload,
                    current_user={"user_id": 2, "role": "user"},
                )

        self.assertEqual(context.exception.status_code, 403)
        create_evaluation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
