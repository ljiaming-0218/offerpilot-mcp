import time
from urllib.parse import urlparse

from backend.crawler.fetcher import fetch_public_page
from backend.crawler.parsers.generic_parser import parse_job_page
from backend.errors import AppError
from backend.repositories import crawler_repository
from backend.schemas.crawler_schema import BatchFetchUrlRequest, FetchUrlRequest, JobImportRequest
from backend.schemas.job_schema import JobCreate
from backend.services import job_service


def fetch_url_and_create_job(payload: FetchUrlRequest) -> dict:
    url = str(payload.url)
    task_id = crawler_repository.create_crawl_task(
        seed_url=url,
        source_site=urlparse(url).netloc,
    )

    try:
        html = fetch_public_page(url)
        parsed = parse_job_page(html)

        job = JobCreate(
            company_name=payload.company_name or parsed.get("company_name") or _infer_company_name(url),
            title=parsed["title"],
            city=payload.city or parsed.get("city"),
            job_type=payload.job_type or parsed.get("job_type"),
            source_url=url,
            description=parsed["description"],
        )

        created_job = job_service.create_job(job)
        crawler_repository.create_crawl_record(
            task_id=task_id,
            source_url=url,
            status="success",
            title=parsed.get("title"),
            raw_text=parsed.get("description"),
            parsed_data=parsed,
            job_id=created_job["job_id"],
        )
        crawler_repository.finish_crawl_task(task_id=task_id, status="success")

        return {
            "status": "success",
            "task_id": task_id,
            "job_id": created_job["job_id"],
            "source_url": url,
            "parsed_job": created_job,
            "message": "岗位网页采集并入库成功",
        }

    except AppError as exc:
        status = "skipped" if exc.error == "DUPLICATE_JOB" else "failed"
        crawler_repository.create_crawl_record(
            task_id=task_id,
            source_url=url,
            status=status,
            error_message=exc.message,
        )
        crawler_repository.finish_crawl_task(
            task_id=task_id,
            status=status,
            error_message=exc.message,
        )
        raise

    except Exception as exc:
        crawler_repository.create_crawl_record(
            task_id=task_id,
            source_url=url,
            status="failed",
            error_message=str(exc),
        )
        crawler_repository.finish_crawl_task(
            task_id=task_id,
            status="failed",
            error_message=str(exc),
        )
        raise AppError(
            error="CRAWL_FAILED",
            message="岗位网页采集失败",
            status_code=400,
            reason=str(exc),
            source_url=url,
        )


def fetch_urls_and_create_jobs(payload: BatchFetchUrlRequest) -> dict:
    results = []

    for index, url in enumerate(payload.urls):
        source_url = str(url)

        try:
            result = fetch_url_and_create_job(FetchUrlRequest(url=url))
            results.append(
                {
                    "status": "success",
                    "source_url": source_url,
                    "job_id": result.get("job_id"),
                    "message": result.get("message"),
                    "parsed_job": result.get("parsed_job"),
                }
            )
        except AppError as exc:
            status = "skipped" if exc.error == "DUPLICATE_JOB" else "failed"
            results.append(
                {
                    "status": status,
                    "source_url": source_url,
                    "error": exc.error,
                    "message": exc.message,
                    **exc.details,
                }
            )

        if index < len(payload.urls) - 1:
            time.sleep(0.5)

    return {
        "total": len(results),
        "success_count": sum(1 for item in results if item["status"] == "success"),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "skipped_count": sum(1 for item in results if item["status"] == "skipped"),
        "results": results,
    }


def list_crawl_tasks(limit: int = 20) -> list[dict]:
    return crawler_repository.list_crawl_tasks(limit=limit)


def list_crawl_records(limit: int = 20) -> list[dict]:
    return crawler_repository.list_crawl_records(limit=limit)


def import_jobs_from_json(payload: JobImportRequest) -> dict:
    created_jobs = []
    skipped_jobs = []

    for job in payload.jobs:
        try:
            created_job = job_service.create_job(job)
            created_jobs.append(created_job)
        except AppError as exc:
            skipped_jobs.append(
                {
                    "title": job.title,
                    "company_name": job.company_name,
                    "error": exc.error,
                    "message": exc.message,
                    **exc.details,
                }
            )

    return {
        "created_count": len(created_jobs),
        "skipped_count": len(skipped_jobs),
        "created_jobs": created_jobs,
        "skipped_jobs": skipped_jobs,
    }


def _infer_company_name(url: str) -> str:
    host = urlparse(url).netloc
    return host or "未知公司"
