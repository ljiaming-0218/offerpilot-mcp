import unittest
from unittest.mock import patch

from backend.errors import AppError
from backend.services import skill_extract_service


SOURCE_TEXT = """大模型应用开发实习生
岗位职责：负责使用 Python 和 FastAPI 开发大模型应用。
任职要求：本科及以上学历，计算机相关专业，通过 CET-6。
熟悉 RAG 和向量检索，有开源社区贡献者优先。
"""


class SkillExtractionNormalizationTests(unittest.TestCase):
    def test_keeps_only_items_with_verbatim_evidence(self) -> None:
        result = {
            "skills": [
                {
                    "skill_name": "Python",
                    "category": "Backend",
                    "importance": "high",
                    "evidence": "使用 Python 和 FastAPI 开发大模型应用",
                },
                {
                    "skill_name": "Kubernetes",
                    "category": "Deployment",
                    "importance": "high",
                    "evidence": "熟悉 Kubernetes",
                },
            ],
            "education_requirements": [
                {"value": "本科及以上", "evidence": "本科及以上学历"},
            ],
            "language_requirements": [
                {"value": "英语六级", "evidence": "通过 CET-6"},
            ],
            "difficulty": "medium",
        }

        skills, requirement = skill_extract_service._normalize_llm_result(result, SOURCE_TEXT)

        self.assertEqual([item["skill_name"] for item in skills], ["Python"])
        self.assertEqual(requirement["education_requirements"], ["本科及以上"])
        self.assertEqual(requirement["language_requirements"], ["英语六级"])

    def test_unknown_category_is_normalized(self) -> None:
        result = {
            "skills": [
                {
                    "skill_name": "Python",
                    "category": "Random Category",
                    "importance": "high",
                    "evidence": "Python",
                }
            ]
        }

        skills, _ = skill_extract_service._normalize_llm_result(result, SOURCE_TEXT)

        self.assertEqual(skills[0]["category"], "Engineering")

    def test_invalid_importance_is_discarded(self) -> None:
        result = {
            "skills": [
                {
                    "skill_name": "Python",
                    "category": "Backend",
                    "importance": "critical",
                    "evidence": "Python",
                }
            ]
        }

        skills, _ = skill_extract_service._normalize_llm_result(result, SOURCE_TEXT)

        self.assertEqual(skills, [])


class SkillExtractionFlowTests(unittest.TestCase):
    def test_uses_llm_result_when_evidence_is_valid(self) -> None:
        with (
            patch("backend.services.skill_extract_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.skill_extract_service.llm_service.chat_json",
                return_value={
                    "skills": [
                        {
                            "skill_name": "RAG",
                            "category": "RAG",
                            "importance": "high",
                            "evidence": "熟悉 RAG 和向量检索",
                        }
                    ],
                    "difficulty": "medium",
                },
            ),
        ):
            skills, _, mode = skill_extract_service._extract_job_requirements(SOURCE_TEXT)

        self.assertEqual(mode, "llm")
        self.assertEqual(skills[0]["skill_name"], "RAG")

    def test_falls_back_to_rules_when_llm_fails(self) -> None:
        with (
            patch("backend.services.skill_extract_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.skill_extract_service.llm_service.chat_json",
                side_effect=AppError(error="LLM_FAILED", message="failed", status_code=502),
            ),
        ):
            skills, requirement, mode = skill_extract_service._extract_job_requirements(SOURCE_TEXT)

        self.assertEqual(mode, "rules_fallback")
        self.assertIn("Python", [item["skill_name"] for item in skills])
        self.assertIn("本科及以上", requirement["education_requirements"])

    def test_empty_skill_result_clears_old_job_skill_links(self) -> None:
        job = {"job_id": 9, "title": "运营实习生", "description": "本科及以上学历"}
        requirement = {
            "technical_skills": [],
            "education_requirements": ["本科及以上"],
            "major_requirements": [],
            "language_requirements": [],
            "experience_requirements": [],
            "soft_skill_requirements": [],
            "bonus_requirements": [],
            "responsibilities": [],
            "job_orientation": "技术岗位",
            "difficulty": "low",
            "summary": "岗位学历要求明确。",
        }

        with (
            patch(
                "backend.services.skill_extract_service.job_repository.get_job_by_id",
                return_value=job,
            ),
            patch(
                "backend.services.skill_extract_service._extract_job_requirements",
                return_value=([], requirement, "llm"),
            ),
            patch(
                "backend.services.skill_extract_service.skill_repository.save_job_skills"
            ) as save_skills,
            patch(
                "backend.services.skill_extract_service.job_repository.save_job_requirement"
            ),
        ):
            skill_extract_service.extract_skills_for_job(9)

        save_skills.assert_called_once_with(job_id=9, skills=[])


if __name__ == "__main__":
    unittest.main()
