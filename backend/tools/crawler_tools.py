from backend.schemas.crawler_schema import FetchUrlRequest
from backend.services import crawler_service


def crawl_job_url(input_data: dict) -> dict:
    payload = FetchUrlRequest(
        url=input_data["url"],
        company_name=input_data.get("company_name"),
        city=input_data.get("city"),
        job_type=input_data.get("job_type", "实习"),
    )

    return crawler_service.fetch_url_and_create_job(payload)
