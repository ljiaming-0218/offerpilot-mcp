from backend.errors import AppError
from backend.schemas.interview_schema import AnswerEvaluationRequest, MockInterviewRequest
from backend.services import interview_service, profile_match_service
from backend.services import study_plan_service


def match_my_profile(input_data: dict) -> dict:
    profile, current_user = _get_owned_profile(input_data)
    return profile_match_service.match_jobs_for_user(
        profile["user_id"],
        current_user=current_user,
    )


def generate_my_mock_interview(input_data: dict) -> dict:
    profile, current_user = _get_owned_profile(input_data)
    payload = MockInterviewRequest(
        user_id=profile["user_id"],
        job_id=input_data["job_id"],
        difficulty=input_data.get("difficulty", "medium"),
    )
    return interview_service.generate_mock_interview(payload, current_user=current_user)


def evaluate_my_interview_answer(input_data: dict) -> dict:
    _, current_user = _get_owned_profile(input_data)
    payload = AnswerEvaluationRequest(**input_data["payload"])
    return interview_service.evaluate_answer(payload, current_user=current_user)


def generate_my_study_plan(input_data: dict) -> dict:
    _, current_user = _get_owned_profile(input_data)
    return study_plan_service.generate_study_plan_for_current_user(current_user)


def _get_owned_profile(input_data: dict) -> tuple[dict, dict]:
    context = input_data.get("_execution_context") or {}
    current_user = context.get("current_user")
    if not isinstance(current_user, dict) or not current_user.get("user_id"):
        raise AppError(
            error="TOOL_CONTEXT_REQUIRED",
            message="该工具只能在已登录的 Agent 会话中调用",
            status_code=403,
        )

    profiles = profile_match_service.list_user_profiles(current_user)
    owned_profiles = [
        profile
        for profile in profiles
        if profile.get("owner_user_id") == current_user["user_id"]
    ]
    if not owned_profiles:
        raise AppError(
            error="USER_PROFILE_NOT_FOUND",
            message="请先创建或上传简历生成用户画像",
            status_code=404,
        )

    return owned_profiles[0], current_user
