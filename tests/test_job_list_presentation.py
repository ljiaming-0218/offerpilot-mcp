import json
import unittest

from backend.repositories.job_repository import _build_job_list_item


class JobListPresentationTests(unittest.TestCase):
    def test_marks_extracted_job_and_builds_compact_summary(self) -> None:
        row = {
            "job_id": 8,
            "skill_count": 3,
            "skill_names": "Agent||MCP||Python",
            "requirement_json": json.dumps(
                {
                    "education_requirements": ["本科及以上"],
                    "language_requirements": ["英语六级"],
                    "major_requirements": ["计算机相关专业"],
                    "experience_requirements": ["有项目经验"],
                },
                ensure_ascii=False,
            ),
        }

        result = _build_job_list_item(row)

        self.assertEqual(result["extraction_status"], "completed")
        self.assertEqual(result["skill_names"], ["Agent", "MCP", "Python"])
        self.assertEqual(result["requirement_highlights"][:2], ["本科及以上", "英语六级"])

    def test_marks_unprocessed_job_without_fabricating_skills(self) -> None:
        result = _build_job_list_item(
            {
                "job_id": 9,
                "skill_count": 0,
                "skill_names": None,
                "requirement_json": None,
            }
        )

        self.assertEqual(result["extraction_status"], "pending")
        self.assertEqual(result["skill_names"], [])
        self.assertEqual(result["requirement_highlights"], [])


if __name__ == "__main__":
    unittest.main()
