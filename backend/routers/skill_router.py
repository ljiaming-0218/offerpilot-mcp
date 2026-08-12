from fastapi import APIRouter, Depends

from backend.dependencies import get_admin_user, get_current_user
from backend.schemas.skill_schema import SkillRead
from backend.services import skill_service
from backend.agent import skill_loader

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillRead])
def list_skills(current_user: dict = Depends(get_current_user)) -> list[SkillRead]:
    return [SkillRead(**skill) for skill in skill_service.list_skills()]

@router.get("/workflows")
def list_skill_workflows(current_user: dict = Depends(get_admin_user)) -> list[dict]:
    return skill_loader.list_skills()
