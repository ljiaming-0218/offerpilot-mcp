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
            }
        )

    return skills


def load_skill(skill_name: str) -> dict | None:
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"

    if not skill_file.is_file():
        return None

    return {
        "skill_name": skill_name,
        "content": skill_file.read_text(encoding="utf-8"),
    }


def _extract_section(content: str, title: str) -> str:
    marker = f"## {title}"
    if marker not in content:
        return ""

    after_marker = content.split(marker, 1)[1]
    section = after_marker.split("## ", 1)[0]

    return section.strip()