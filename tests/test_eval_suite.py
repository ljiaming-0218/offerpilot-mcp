import json
import unittest
from pathlib import Path

from eval.run_evaluations import run_all


EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


class EvaluationAssetTests(unittest.TestCase):
    def test_sample_jobs_are_explicit_non_production_fixtures(self) -> None:
        jobs = json.loads((EVAL_DIR / "sample_jobs.json").read_text(encoding="utf-8"))

        self.assertEqual(len(jobs), 10)
        self.assertTrue(all(job.get("is_fixture") is True for job in jobs))
        self.assertEqual(len({job["fixture_id"] for job in jobs}), len(jobs))

    def test_deterministic_evaluation_suite_passes(self) -> None:
        report = run_all()

        self.assertEqual(report["passed"], report["total"], report["metrics"])
        self.assertGreaterEqual(report["total"], 50)


if __name__ == "__main__":
    unittest.main()
