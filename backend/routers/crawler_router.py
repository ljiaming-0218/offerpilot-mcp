from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_admin_user, get_current_user
from backend.schemas.crawler_schema import (
    BatchFetchUrlRequest,
    BatchFetchUrlResult,
    CrawlRecordRead,
    CrawlTaskRead,
    FetchUrlRequest,
    FetchUrlResult,
    JobImportRequest,
    JobImportResult,
)
from backend.services import crawler_service


router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.post("/fetch-url", response_model=FetchUrlResult)
def fetch_url(payload: FetchUrlRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return crawler_service.fetch_url_and_create_job(payload)


@router.post("/fetch-urls", response_model=BatchFetchUrlResult)
def fetch_urls(payload: BatchFetchUrlRequest, current_user: dict = Depends(get_admin_user)) -> dict:
    return crawler_service.fetch_urls_and_create_jobs(payload)


@router.post("/import-json", response_model=JobImportResult)
def import_jobs_from_json(payload: JobImportRequest, current_user: dict = Depends(get_admin_user)) -> dict:
    return crawler_service.import_jobs_from_json(payload)


@router.get("/tasks", response_model=list[CrawlTaskRead])
def list_crawl_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
) -> list[dict]:
    return crawler_service.list_crawl_tasks(limit=limit)


@router.get("/records", response_model=list[CrawlRecordRead])
def list_crawl_records(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
) -> list[dict]:
    return crawler_service.list_crawl_records(limit=limit)
