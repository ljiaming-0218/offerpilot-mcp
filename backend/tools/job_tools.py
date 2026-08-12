from backend.services import job_service
from backend.services import skill_extract_service


def search_jobs(input_data: dict) -> list[dict]:
    return job_service.list_jobs()


def get_job_detail(input_data: dict) -> dict:
    return job_service.get_job(input_data["job_id"])


def get_job_requirements(input_data: dict) -> dict:
    return job_service.get_job_requirements(input_data["job_id"])


def extract_skills(input_data: dict) -> dict:
    return skill_extract_service.extract_skills_for_job(input_data["job_id"])
