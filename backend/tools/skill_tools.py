from backend.services import skill_service


def list_skills(input_data: dict) -> list[dict]:
    return skill_service.list_skills()