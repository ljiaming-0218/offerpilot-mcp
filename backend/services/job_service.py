from backend.repositories import job_repository
from backend.schemas.job_schema import JobCreate
from backend.errors import AppError
from backend.services import skill_extract_service

def create_job(payload: JobCreate) -> dict:
    data = payload.model_dump()
    existing_job = job_repository.find_duplicate_job(data)

    if existing_job is not None:
        raise AppError(
            error="DUPLICATE_JOB",
            message="岗位已存在，请勿重复录入",
            status_code=409,
            existing_job_id=existing_job["job_id"],
        )

    return job_repository.create_job(data)


def list_jobs() -> list[dict]:
    return job_repository.list_jobs()


def get_job(job_id: int) -> dict:
    job = job_repository.get_job_by_id(job_id)

    if job is None:
        raise AppError(
            error="JOB_NOT_FOUND",
            message="岗位不存在",
            status_code=404,
        )

    return job


def extract_skills_for_unprocessed_jobs(limit: int = 20) -> dict:
    jobs = job_repository.list_jobs_without_skills(limit=limit)

    success_job_ids = []
    failed_jobs = []

    for job in jobs:
        job_id = job["job_id"]

        try:
            skill_extract_service.extract_skills_for_job(job_id)
            success_job_ids.append(job_id)
        except AppError as exc:
            failed_jobs.append(
                {
                    "job_id": job_id,
                    "title": job["title"],
                    "error": exc.error,
                    "message": exc.message,
                }
            )

    return {
        "total": len(jobs),
        "success_count": len(success_job_ids),
        "failed_count": len(failed_jobs),
        "success_job_ids": success_job_ids,
        "failed_jobs": failed_jobs,
    }


def extract_requirements_for_unprocessed_jobs(limit: int = 20) -> dict:
    jobs = job_repository.list_jobs_without_requirement(limit=limit)

    success_job_ids = []
    failed_jobs = []

    for job in jobs:
        job_id = job["job_id"]

        try:
            skill_extract_service.extract_skills_for_job(job_id)
            success_job_ids.append(job_id)
        except AppError as exc:
            failed_jobs.append(
                {
                    "job_id": job_id,
                    "title": job["title"],
                    "error": exc.error,
                    "message": exc.message,
                }
            )

    return {
        "total": len(jobs),
        "success_count": len(success_job_ids),
        "failed_count": len(failed_jobs),
        "success_job_ids": success_job_ids,
        "failed_jobs": failed_jobs,
    }
