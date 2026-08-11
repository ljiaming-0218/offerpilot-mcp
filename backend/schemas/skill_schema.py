from pydantic import BaseModel


class ExtractedSkill(BaseModel):
    skill_name: str
    category: str
    importance: str


class SkillExtractResult(BaseModel):
    job_id: int
    skills: list[ExtractedSkill]
    requirement: dict
    job_orientation: str
    difficulty: str
    summary: str

class SkillRead(BaseModel):
    skill_id: int
    skill_name: str
    category: str | None = None
    job_count: int
