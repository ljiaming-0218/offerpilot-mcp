from backend.services import job_service
from backend.services import skill_extract_service

DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 50
MAX_SEARCH_OFFSET = 10_000


def search_jobs(input_data: dict) -> dict:
    filters = {
        "keyword": _clean_text(input_data.get("keyword")),
        "city": _clean_text(input_data.get("city")),
        "job_type": _clean_text(input_data.get("job_type")),
        "skill": _clean_text(input_data.get("skill")),
        "extraction_status": _clean_extraction_status(input_data.get("extraction_status")),
    }
    clean_filters = {key: value for key, value in filters.items() if value}
    limit = _bounded_int(
        input_data.get("limit"),
        default=DEFAULT_SEARCH_LIMIT,
        minimum=1,
        maximum=MAX_SEARCH_LIMIT,
    )
    offset = _bounded_int(
        input_data.get("offset"),
        default=0,
        minimum=0,
        maximum=MAX_SEARCH_OFFSET,
    )

    rows = job_service.list_jobs(
        **clean_filters,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(rows) > limit
    jobs = rows[:limit]

    return {
        "jobs": jobs,
        "returned": len(jobs),
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "filters": clean_filters,
    }


def get_job_detail(input_data: dict) -> dict:
    return job_service.get_job(input_data["job_id"])


def get_job_requirements(input_data: dict) -> dict:
    return job_service.get_job_requirements(input_data["job_id"])


def extract_skills(input_data: dict) -> dict:
    return skill_extract_service.extract_skills_for_job(input_data["job_id"])


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:120] if text else None


def _clean_extraction_status(value) -> str | None:
    text = _clean_text(value)
    if text in {"completed", "skills_only", "pending"}:
        return text
    return None


def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))
