import re
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[2] / ".skills"


def list_skills() -> list[dict]:
    skills = []

    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in SKILLS_DIR.iterdir():
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.is_file():
            continue

        content = skill_file.read_text(encoding="utf-8")
        skills.append(
            {
                "skill_name": skill_dir.name,
                "description": _extract_section(content, "适用场景"),
                "trigger_keywords": _extract_section(content, "触发关键词"),
                "allowed_tools": _extract_list(content, "可调用工具"),
            }
        )

    return sorted(skills, key=lambda item: item["skill_name"])


def load_skill(skill_name: str) -> dict | None:
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"

    if not skill_file.is_file():
        return None

    content = skill_file.read_text(encoding="utf-8")
    return {
        "skill_name": skill_name,
        "content": content,
        "description": _extract_section(content, "适用场景"),
        "trigger_keywords": _extract_keywords(content),
        "execution_steps": _extract_list(content, "执行步骤"),
        "allowed_tools": _extract_list(content, "可调用工具"),
        "quality_checks": _extract_list(content, "质量检查"),
        "failure_handling": _extract_section(content, "失败处理"),
    }


def _extract_section(content: str, title: str) -> str:
    marker = f"## {title}"
    if marker not in content:
        return ""

    after_marker = content.split(marker, 1)[1]
    section = after_marker.split("## ", 1)[0]

    return section.strip()


def _extract_list(content: str, title: str) -> list[str]:
    section = _extract_section(content, title)
    if not section:
        return []

    items = []
    for line in section.splitlines():
        item = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line).strip()
        if item:
            items.append(item)
    return items


def _extract_keywords(content: str) -> list[str]:
    section = _extract_section(content, "触发关键词")
    return [item.strip() for item in re.split(r"[、,，\n]", section) if item.strip()]
