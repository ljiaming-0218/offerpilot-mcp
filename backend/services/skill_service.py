from backend.repositories import skill_repository


def list_skills() -> list[dict]:
    return skill_repository.list_skills()