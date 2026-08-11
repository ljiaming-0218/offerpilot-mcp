from fastapi import APIRouter, Path, status

from backend.schemas.job_schema import JobCreate, JobListItem, JobRead
from backend.services import job_service
from backend.schemas.skill_schema import SkillExtractResult
from backend.services import skill_extract_service
from backend.schemas.job_schema import BatchSkillExtractResult

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate) -> dict:
    return job_service.create_job(payload)


@router.get("", response_model=list[JobListItem])
def list_jobs() -> list[dict]:
    return job_service.list_jobs()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int = Path(..., ge=1)) -> dict:
    return job_service.get_job(job_id)


@router.post("/{job_id}/extract-skills", response_model=SkillExtractResult)
def extract_job_skills(job_id: int = Path(..., ge=1)) -> dict:
    return skill_extract_service.extract_skills_for_job(job_id)


@router.post("/extract-skills/batch", response_model=BatchSkillExtractResult)
def extract_skills_batch(limit: int = 20) -> dict:
    return job_service.extract_skills_for_unprocessed_jobs(limit=limit)


@router.post("/extract-requirements/batch", response_model=BatchSkillExtractResult)
def extract_requirements_batch(limit: int = 20) -> dict:
    return job_service.extract_requirements_for_unprocessed_jobs(limit=limit)
