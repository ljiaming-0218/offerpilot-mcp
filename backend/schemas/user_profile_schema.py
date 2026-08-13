from pydantic import BaseModel, Field, field_validator


class UserProfileUpsert(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=200)
    target_roles: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    preferred_work_type: str | None = Field(default=None, max_length=80)
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)

    @field_validator("user_id", "name", "education", "preferred_work_type")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("target_roles", "target_cities", "skills", "projects", "weaknesses")
    @classmethod
    def clean_list(cls, values: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for value in values:
            item = value.strip()
            if item and item not in seen:
                cleaned.append(item)
                seen.add(item)
        return cleaned


class UserProfileRead(UserProfileUpsert):
    owner_user_id: int | None = None
    owner_username: str | None = None
    created_at: str
    updated_at: str


class ResumeProfileDraft(BaseModel):
    user_id: str | None = None
    name: str | None = None
    education: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    preferred_work_type: str | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class ResumeParseSource(BaseModel):
    filename: str
    file_type: str
    text_length: int
    parse_method: str
    warnings: list[str] = Field(default_factory=list)


class ResumeParseResult(BaseModel):
    profile: ResumeProfileDraft
    text_preview: str
    source: ResumeParseSource


class JobMatchItem(BaseModel):
    job_id: int
    title: str
    company_name: str
    city: str | None = None
    job_type: str | None = None
    source_url: str | None = None
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    job_skills: list[str]
    requirement_checks: dict


class ProfileMatchResult(BaseModel):
    user_id: str
    total_jobs: int
    matched_jobs: int
    user_skills: list[str]
    matches: list[JobMatchItem]


class StudyPlanItem(BaseModel):
    priority: int
    skill_name: str
    target_job_count: int
    matched_job_examples: list[str] = Field(default_factory=list)
    action: str


class StudyPlanResult(BaseModel):
    user_id: str
    total_jobs: int
    matched_jobs: int
    focus_skills: list[str] = Field(default_factory=list)
    plan_items: list[StudyPlanItem] = Field(default_factory=list)
    message: str
