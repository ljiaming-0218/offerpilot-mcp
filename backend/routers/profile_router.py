from fastapi import APIRouter, Depends, File, Path, UploadFile

from backend.dependencies import get_current_user
from backend.schemas.user_profile_schema import (
    ProfileMatchResult,
    ResumeParseResult,
    StudyPlanResult,
    UserProfileRead,
    UserProfileUpsert,
)
from backend.services import profile_match_service, resume_parse_service, study_plan_service


router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=UserProfileRead)
def upsert_user_profile(payload: UserProfileUpsert, current_user: dict = Depends(get_current_user)) -> dict:
    return profile_match_service.upsert_user_profile(payload, current_user=current_user)


@router.get("", response_model=list[UserProfileRead])
def list_user_profiles(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return profile_match_service.list_user_profiles(current_user)


@router.post("/parse-resume", response_model=ResumeParseResult)
async def parse_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    content = await file.read()
    return resume_parse_service.parse_resume(file.filename or "resume", content)


@router.post("/study-plan", response_model=StudyPlanResult)
def generate_study_plan(current_user: dict = Depends(get_current_user)) -> dict:
    return study_plan_service.generate_study_plan_for_current_user(current_user)


@router.get("/{user_id}", response_model=UserProfileRead)
def get_user_profile(
    user_id: str = Path(..., min_length=1, max_length=80),
    current_user: dict = Depends(get_current_user),
) -> dict:
    return profile_match_service.get_user_profile(user_id, current_user=current_user)


@router.get("/{user_id}/matches", response_model=ProfileMatchResult)
def match_jobs_for_user(
    user_id: str = Path(..., min_length=1, max_length=80),
    current_user: dict = Depends(get_current_user),
) -> dict:
    return profile_match_service.match_jobs_for_user(user_id, current_user=current_user)
