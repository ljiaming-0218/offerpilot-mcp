from pydantic import BaseModel, Field, field_validator


class JobCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=120)
    industry: str | None = Field(default=None, max_length=80)
    title: str = Field(..., min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    job_type: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=500)
    description: str = Field(..., min_length=1)

    @field_validator("company_name", "title", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value

    @field_validator("industry", "city", "job_type", "source_url")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class JobRead(BaseModel):
    job_id: int
    company_id: int
    company_name: str
    industry: str | None = None
    title: str
    city: str | None = None
    job_type: str | None = None
    source_url: str | None = None
    requirement_json: dict | None = None
    description: str
    created_at: str
    updated_at: str


class JobListItem(BaseModel):
    job_id: int
    company_id: int
    company_name: str
    title: str
    city: str | None = None
    job_type: str | None = None
    source_url: str | None = None
    description_preview: str
    created_at: str

class BatchSkillExtractResult(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_job_ids: list[int]
    failed_jobs: list[dict]
