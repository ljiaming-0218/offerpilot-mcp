import json
import unittest
from unittest.mock import patch

from backend.repositories.job_repository import _build_job_list_item
from backend.tools import job_tools


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

    def test_search_jobs_tool_clamps_context_size_and_returns_page_metadata(self) -> None:
        rows = [{"job_id": index} for index in range(1, 52)]

        with patch(
            "backend.tools.job_tools.job_service.list_jobs",
            return_value=rows,
        ) as list_jobs:
            result = job_tools.search_jobs(
                {
                    "keyword": " Agent ",
                    "city": " 北京 ",
                    "skill": "RAG",
                    "extraction_status": "completed",
                    "limit": 500,
                    "offset": -10,
                }
            )

        self.assertEqual(result["limit"], 50)
        self.assertEqual(result["offset"], 0)
        self.assertTrue(result["has_more"])
        self.assertEqual(result["returned"], 50)
        self.assertEqual(result["jobs"][0]["job_id"], 1)
        self.assertEqual(result["filters"]["keyword"], "Agent")
        self.assertEqual(
            list_jobs.call_args.kwargs,
            {
                "keyword": "Agent",
                "city": "北京",
                "skill": "RAG",
                "extraction_status": "completed",
                "limit": 51,
                "offset": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
