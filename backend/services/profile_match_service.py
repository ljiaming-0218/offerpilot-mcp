from backend.errors import AppError
from backend.repositories import job_repository, user_profile_repository
from backend.schemas.user_profile_schema import UserProfileUpsert


def upsert_user_profile(payload: UserProfileUpsert, current_user: dict) -> dict:
    existing_profile = user_profile_repository.get_user_profile(payload.user_id)
    if existing_profile is not None and not _can_access_profile(existing_profile, current_user):
        raise AppError(
            error="PROFILE_FORBIDDEN",
            message="不能修改其他用户创建的画像",
            status_code=403,
        )

    data = payload.model_dump()
    data["owner_user_id"] = current_user["user_id"]
    return user_profile_repository.upsert_user_profile(data)


def get_user_profile(user_id: str, current_user: dict | None = None) -> dict:
    profile = user_profile_repository.get_user_profile(user_id)

    if profile is None:
        raise AppError(
            error="USER_PROFILE_NOT_FOUND",
            message="用户画像不存在",
            status_code=404,
        )

    if current_user is not None and not _can_access_profile(profile, current_user):
        raise AppError(
            error="PROFILE_FORBIDDEN",
            message="不能查看其他用户创建的画像",
            status_code=403,
        )

    return profile


def list_user_profiles(current_user: dict) -> list[dict]:
    if current_user.get("role") == "admin":
        return user_profile_repository.list_user_profiles()
    return user_profile_repository.list_user_profiles(owner_user_id=current_user["user_id"])


def match_jobs_for_user(user_id: str, current_user: dict | None = None) -> dict:
    profile = get_user_profile(user_id, current_user=current_user)
    user_skills = profile.get("skills", [])
    normalized_user_skills = {_normalize_skill(skill): skill for skill in user_skills}
    profile_text = _build_profile_text(profile)
    jobs = job_repository.list_jobs_with_skills()

    matches = []
    for job in jobs:
        job_skill_names = _unique_skill_names(job["skills"])
        matched_skills = [
            skill
            for skill in job_skill_names
            if _normalize_skill(skill) in normalized_user_skills
        ]
        missing_skills = [
            skill
            for skill in job_skill_names
            if _normalize_skill(skill) not in normalized_user_skills
        ]
        match_score = round(len(matched_skills) / len(job_skill_names) * 100) if job_skill_names else 0

        matches.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "company_name": job["company_name"],
                "city": job.get("city"),
                "job_type": job.get("job_type"),
                "source_url": job.get("source_url"),
                "match_score": match_score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "job_skills": job_skill_names,
                "requirement_checks": _check_requirements(
                    requirement=job.get("requirement_json"),
                    profile=profile,
                    profile_text=profile_text,
                ),
            }
        )

    matches.sort(key=lambda item: (item["match_score"], len(item["matched_skills"]), item["job_id"]), reverse=True)

    return {
        "user_id": user_id,
        "total_jobs": len(jobs),
        "matched_jobs": sum(1 for item in matches if item["matched_skills"]),
        "user_skills": user_skills,
        "matches": matches,
    }


def _can_access_profile(profile: dict, current_user: dict) -> bool:
    if current_user.get("role") == "admin":
        return True
    return profile.get("owner_user_id") == current_user.get("user_id")


def _normalize_skill(skill: str) -> str:
    return skill.strip().lower()


def _unique_skill_names(skills: list[dict]) -> list[str]:
    result = []
    seen = set()
    for skill in skills:
        skill_name = skill["skill_name"].strip()
        normalized = _normalize_skill(skill_name)
        if normalized and normalized not in seen:
            result.append(skill_name)
            seen.add(normalized)
    return result


def _build_profile_text(profile: dict) -> str:
    parts = [
        profile.get("education") or "",
        profile.get("preferred_work_type") or "",
        *profile.get("target_roles", []),
        *profile.get("target_cities", []),
        *profile.get("skills", []),
        *profile.get("projects", []),
        *profile.get("weaknesses", []),
    ]
    return "\n".join(parts).lower()


def _check_requirements(requirement: dict | None, profile: dict, profile_text: str) -> dict:
    if not requirement:
        return {
            "status": "not_extracted",
            "matched": {},
            "missing": {},
            "unstated": ["尚未抽取完整岗位要求"],
        }

    checks = {
        "education_requirements": _match_requirement_items(
            requirement.get("education_requirements", []),
            profile_text,
            aliases={
                "本科及以上": ["本科", "硕士", "研究生", "博士"],
                "硕士": ["硕士", "研究生", "博士"],
                "博士": ["博士"],
                "本科": ["本科", "硕士", "研究生", "博士"],
            },
        ),
        "major_requirements": _match_requirement_items(requirement.get("major_requirements", []), profile_text),
        "language_requirements": _match_requirement_items(
            requirement.get("language_requirements", []),
            profile_text,
            aliases={
                "英语四级": ["英语四级", "四级", "cet-4", "cet4", "英语六级", "六级", "cet-6", "cet6"],
                "英语六级": ["英语六级", "六级", "cet-6", "cet6"],
                "英文文档阅读": ["英文文档", "英语读写", "英文读写", "英语六级", "六级"],
            },
        ),
        "experience_requirements": _match_requirement_items(requirement.get("experience_requirements", []), profile_text),
        "soft_skill_requirements": _match_requirement_items(requirement.get("soft_skill_requirements", []), profile_text),
        "bonus_requirements": _match_requirement_items(requirement.get("bonus_requirements", []), profile_text),
    }

    matched = {field: value["matched"] for field, value in checks.items() if value["matched"]}
    missing = {field: value["missing"] for field, value in checks.items() if value["missing"]}
    unstated = [field for field, value in checks.items() if not value["matched"] and not value["missing"]]

    return {
        "status": "checked",
        "matched": matched,
        "missing": missing,
        "unstated": unstated,
    }


def _match_requirement_items(items: list[str], profile_text: str, aliases: dict[str, list[str]] | None = None) -> dict:
    matched = []
    missing = []

    for item in items:
        candidates = aliases.get(item, [item]) if aliases else [item]
        if any(candidate.lower() in profile_text for candidate in candidates):
            matched.append(item)
        else:
            missing.append(item)

    return {"matched": matched, "missing": missing}
