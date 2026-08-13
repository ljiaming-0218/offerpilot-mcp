import unittest
from unittest.mock import patch

from backend.errors import AppError
from backend.services import sql_guard_service, text2sql_service


class SqlGuardAstTests(unittest.TestCase):
    def test_allows_combined_city_and_skill_filters(self) -> None:
        result = sql_guard_service.check_sql_safety(
            """
            SELECT j.job_id
            FROM jobs j
            JOIN job_skills js ON js.job_id = j.job_id
            JOIN skills s ON s.skill_id = js.skill_id
            WHERE j.city LIKE '%杭州%'
              AND LOWER(s.skill_name) = LOWER('Agent')
            """
        )

        self.assertTrue(result["safe"], result["reason"])

    def test_allows_expected_job_query_and_adds_limit(self) -> None:
        result = sql_guard_service.check_sql_safety(
            """
            SELECT j.job_id, c.company_name, j.title
            FROM jobs j
            JOIN companies c ON c.company_id = j.company_id
            WHERE j.city LIKE '%北京%'
            ORDER BY j.job_id DESC
            """
        )

        self.assertTrue(result["safe"])
        self.assertIn("LIMIT 100", result["sql"])

    def test_allows_aggregate_alias_in_order_by(self) -> None:
        result = sql_guard_service.check_sql_safety(
            """
            SELECT s.skill_name, COUNT(js.job_id) AS job_count
            FROM skills s
            JOIN job_skills js ON js.skill_id = s.skill_id
            GROUP BY s.skill_name
            ORDER BY job_count DESC
            """
        )

        self.assertTrue(result["safe"])

    def test_allows_common_readonly_filters_and_date_functions(self) -> None:
        queries = [
            "SELECT job_id FROM jobs WHERE city = '北京' OR city = '上海'",
            "SELECT job_id FROM jobs WHERE city IN ('北京', '上海')",
            "SELECT job_id FROM jobs WHERE city IS NOT NULL",
            "SELECT YEAR(created_at), MONTH(created_at), DATE(created_at) FROM jobs",
        ]

        for sql in queries:
            with self.subTest(sql=sql):
                result = sql_guard_service.check_sql_safety(sql)
                self.assertTrue(result["safe"], result["reason"])

    def test_blocks_invalid_unqualified_columns_and_unknown_wildcard_aliases(self) -> None:
        invalid_column = sql_guard_service.check_sql_safety(
            "SELECT company_name FROM jobs"
        )
        ambiguous_column = sql_guard_service.check_sql_safety(
            "SELECT city FROM jobs j JOIN companies c ON c.company_id = j.company_id"
        )
        invalid_wildcard = sql_guard_service.check_sql_safety(
            "SELECT unknown_alias.* FROM jobs j"
        )

        self.assertFalse(invalid_column["safe"])
        self.assertFalse(ambiguous_column["safe"])
        self.assertFalse(invalid_wildcard["safe"])

    def test_blocks_select_into_and_excessive_offset(self) -> None:
        into_result = sql_guard_service.check_sql_safety(
            "SELECT job_id INTO OUTFILE '/tmp/jobs.txt' FROM jobs"
        )
        offset_result = sql_guard_service.check_sql_safety(
            "SELECT job_id FROM jobs LIMIT 10 OFFSET 10000001"
        )

        self.assertFalse(into_result["safe"])
        self.assertFalse(offset_result["safe"])

    def test_clamps_large_limit(self) -> None:
        result = sql_guard_service.check_sql_safety("SELECT job_id FROM jobs LIMIT 500")

        self.assertTrue(result["safe"])
        self.assertIn("LIMIT 100", result["sql"])

    def test_blocks_private_table(self) -> None:
        result = sql_guard_service.check_sql_safety("SELECT username FROM app_users")

        self.assertFalse(result["safe"])
        self.assertIn("app_users", result["reason"])

    def test_blocks_system_schema(self) -> None:
        result = sql_guard_service.check_sql_safety(
            "SELECT table_name FROM information_schema.tables"
        )

        self.assertFalse(result["safe"])

    def test_blocks_unknown_column(self) -> None:
        result = sql_guard_service.check_sql_safety("SELECT salary FROM jobs")

        self.assertFalse(result["safe"])
        self.assertIn("salary", result["reason"])

    def test_blocks_dangerous_function(self) -> None:
        result = sql_guard_service.check_sql_safety("SELECT SLEEP(1) FROM jobs")

        self.assertFalse(result["safe"])
        self.assertIn("sleep", result["reason"])

    def test_blocks_union_and_subquery(self) -> None:
        union_result = sql_guard_service.check_sql_safety(
            "SELECT job_id FROM jobs UNION SELECT skill_id FROM skills"
        )
        subquery_result = sql_guard_service.check_sql_safety(
            "SELECT job_id FROM jobs WHERE company_id IN (SELECT company_id FROM companies)"
        )

        self.assertFalse(union_result["safe"])
        self.assertFalse(subquery_result["safe"])

    def test_blocks_locking_reads_and_session_variables(self) -> None:
        lock_result = sql_guard_service.check_sql_safety(
            "SELECT job_id FROM jobs FOR UPDATE"
        )
        variable_result = sql_guard_service.check_sql_safety(
            "SELECT @@version FROM jobs"
        )

        self.assertFalse(lock_result["safe"])
        self.assertFalse(variable_result["safe"])


class IntelligentText2SqlTests(unittest.TestCase):
    def test_uses_llm_generated_sql_when_available(self) -> None:
        with (
            patch("backend.services.text2sql_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.text2sql_service.llm_service.chat_json",
                return_value={"sql": "SELECT job_id, title FROM jobs WHERE city LIKE '%北京%'"},
            ),
            patch(
                "backend.services.text2sql_service.text2sql_repository.execute_readonly_sql",
                return_value=[{"job_id": 1, "title": "AI 工程师"}],
            ) as execute_sql,
        ):
            result = text2sql_service.query_jobs_by_question("北京有哪些 AI 岗位？")

        self.assertEqual(result["generation_mode"], "llm")
        self.assertEqual(len(result["rows"]), 1)
        self.assertIn("LIMIT 100", execute_sql.call_args.args[0])

    def test_falls_back_to_rules_when_llm_fails(self) -> None:
        with (
            patch("backend.services.text2sql_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.text2sql_service.llm_service.chat_json",
                side_effect=AppError(error="LLM_FAILED", message="failed", status_code=502),
            ),
            patch(
                "backend.services.text2sql_service.text2sql_repository.execute_readonly_sql",
                return_value=[],
            ),
        ):
            result = text2sql_service.query_jobs_by_question("成都有哪些岗位？")

        self.assertEqual(result["generation_mode"], "rules_fallback")
        self.assertIn("成都", result["sql"])

    def test_rules_fallback_supports_company_statistics(self) -> None:
        with (
            patch("backend.services.text2sql_service.llm_service.is_llm_available", return_value=False),
            patch(
                "backend.services.text2sql_service.text2sql_repository.execute_readonly_sql",
                return_value=[],
            ),
        ):
            result = text2sql_service.query_jobs_by_question(
                "按公司统计北京的岗位数量，只显示岗位数最多的前5家公司"
            )

        self.assertEqual(result["generation_mode"], "rules_fallback")
        self.assertIn("COUNT", result["sql"])
        self.assertIn("北京", result["sql"])
        self.assertIn("LIMIT 5", result["sql"])

    def test_rules_fallback_rejects_unrecognized_question(self) -> None:
        with patch(
            "backend.services.text2sql_service.llm_service.is_llm_available",
            return_value=False,
        ):
            with self.assertRaises(AppError) as context:
                text2sql_service.query_jobs_by_question("帮我深入分析哪些岗位最适合转行")

        self.assertEqual(context.exception.error, "TEXT2SQL_FALLBACK_UNSUPPORTED")

    def test_does_not_execute_unsafe_llm_sql(self) -> None:
        with (
            patch("backend.services.text2sql_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.text2sql_service.llm_service.chat_json",
                side_effect=[
                    {"sql": "SELECT username FROM app_users"},
                    {"sql": "SELECT username FROM app_users"},
                ],
            ),
            patch(
                "backend.services.text2sql_service.text2sql_repository.execute_readonly_sql"
            ) as execute_sql,
        ):
            with self.assertRaises(AppError) as context:
                text2sql_service.query_jobs_by_question("查询全部用户")

        self.assertEqual(context.exception.error, "UNSAFE_SQL")
        execute_sql.assert_not_called()

    def test_repairs_unsafe_llm_sql_once(self) -> None:
        with (
            patch("backend.services.text2sql_service.llm_service.is_llm_available", return_value=True),
            patch(
                "backend.services.text2sql_service.llm_service.chat_json",
                side_effect=[
                    {"sql": "SELECT salary FROM jobs"},
                    {"sql": "SELECT job_id, title FROM jobs WHERE city = '北京' LIMIT 5"},
                ],
            ) as chat_json,
            patch(
                "backend.services.text2sql_service.text2sql_repository.execute_readonly_sql",
                return_value=[],
            ),
        ):
            result = text2sql_service.query_jobs_by_question("北京薪资最高的5个岗位")

        self.assertEqual(result["generation_mode"], "llm_repaired")
        self.assertTrue(result["safe"])
        self.assertEqual(chat_json.call_count, 2)


if __name__ == "__main__":
    unittest.main()
