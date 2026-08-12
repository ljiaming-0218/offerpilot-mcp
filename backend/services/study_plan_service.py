from collections import Counter

from backend.errors import AppError
from backend.services import profile_match_service


MAX_RECOMMENDED_SKILLS = 5


def generate_study_plan_for_current_user(current_user: dict) -> dict:
    profile = _get_owned_profile(current_user)
    match_result = profile_match_service.match_jobs_for_user(
        profile["user_id"],
        current_user=current_user,
    )
    priorities = _build_skill_priorities(match_result.get("matches", []))

    return {
        "user_id": profile["user_id"],
        "total_jobs": match_result.get("total_jobs", 0),
        "matched_jobs": match_result.get("matched_jobs", 0),
        "focus_skills": [item["skill_name"] for item in priorities],
        "plan_items": [
            {
                "priority": index,
                "skill_name": item["skill_name"],
                "target_job_count": item["target_job_count"],
                "matched_job_examples": item["job_examples"],
                "action": f"围绕 {item['skill_name']} 完成一个可展示的练习或项目改造，并补充到简历画像。",
            }
            for index, item in enumerate(priorities, start=1)
        ],
        "message": _build_message(priorities),
    }


def _get_owned_profile(current_user: dict) -> dict:
    profiles = profile_match_service.list_user_profiles(current_user)
    owner_user_id = current_user["user_id"]
    owned_profiles = [
        profile
        for profile in profiles
        if profile.get("owner_user_id") == owner_user_id
    ]
    if not owned_profiles:
        raise AppError(
            error="USER_PROFILE_NOT_FOUND",
            message="请先创建或上传简历生成用户画像",
            status_code=404,
        )
    return owned_profiles[0]


def _build_skill_priorities(matches: list[dict]) -> list[dict]:
    counts = Counter()
    examples: dict[str, list[str]] = {}

    for match in matches:
        job_label = f"{match.get('company_name', '未知公司')}·{match.get('title', '未知岗位')}"
        for skill in match.get("missing_skills", []):
            normalized = skill.strip()
            if not normalized:
                continue
            counts[normalized] += 1
            examples.setdefault(normalized, [])
            if job_label not in examples[normalized] and len(examples[normalized]) < 2:
                examples[normalized].append(job_label)

    return [
        {
            "skill_name": skill_name,
            "target_job_count": count,
            "job_examples": examples[skill_name],
        }
        for skill_name, count in counts.most_common(MAX_RECOMMENDED_SKILLS)
    ]


def _build_message(priorities: list[dict]) -> str:
    if not priorities:
        return "当前岗位数据没有发现明确技能缺口，请继续采集岗位并执行技能抽取后再生成学习计划。"
    return f"已根据真实岗位缺口生成 {len(priorities)} 项学习优先级。"
