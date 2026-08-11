from pydantic import BaseModel, Field, HttpUrl

from backend.schemas.job_schema import JobCreate, JobRead


class FetchUrlRequest(BaseModel):
    url: HttpUrl
    company_name: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    job_type: str | None = Field(default=None, max_length=80)


class FetchUrlResult(BaseModel):
    status: str
    task_id: int | None = None
    job_id: int | None = None
    source_url: str
    parsed_job: dict | None = None
    message: str


class BatchFetchUrlRequest(BaseModel):
    urls: list[HttpUrl] = Field(..., min_length=1, max_length=50)


class BatchFetchUrlResult(BaseModel):
    total: int
    success_count: int
    failed_count: int
    skipped_count: int
    results: list[dict]


class JobImportRequest(BaseModel):
    jobs: list[JobCreate] = Field(..., min_length=1)


class JobImportResult(BaseModel):
    created_count: int
    skipped_count: int
    created_jobs: list[JobRead]
    skipped_jobs: list[dict]


class CrawlTaskRead(BaseModel):
    task_id: int
    seed_url: str
    source_site: str | None = None
    status: str
    error_message: str | None = None
    created_at: str
    updated_at: str


class CrawlRecordRead(BaseModel):
    record_id: int
    task_id: int
    job_id: int | None = None
    source_url: str
    title: str | None = None
    raw_text_preview: str | None = None
    parsed_json: dict | None = None
    status: str
    error_message: str | None = None
    crawled_at: str
