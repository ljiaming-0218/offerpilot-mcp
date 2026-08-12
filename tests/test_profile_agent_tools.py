import unittest
from unittest.mock import patch

from backend.errors import AppError
from backend.tools import profile_tools


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


if __name__ == "__main__":
    unittest.main()
