import unittest
from unittest.mock import Mock, patch

import requests

from backend.errors import AppError
from backend.services import llm_service, resume_parse_service


class LlmErrorHandlingTests(unittest.TestCase):
    @patch("backend.services.llm_service._resolve_llm_config")
    @patch("backend.services.llm_service.requests.post")
    def test_rate_limit_response_has_specific_error(self, post: Mock, resolve: Mock) -> None:
        resolve.return_value = ("https://openrouter.ai/api/v1", "secret", "free-model")
        response = Mock(status_code=429, headers={})
        response.json.return_value = {
            "error": {"message": "Rate limit exceeded: free-models-per-day"}
        }
        post.return_value = response

        with self.assertRaises(AppError) as context:
            llm_service.chat_json("system", "user")

        self.assertEqual(context.exception.error, "LLM_RATE_LIMITED")
        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.details["provider_status"], 429)
        self.assertNotIn("secret", str(context.exception.details))

    @patch("backend.services.llm_service._resolve_llm_config")
    @patch("backend.services.llm_service.requests.post")
    def test_timeout_has_specific_error(self, post: Mock, resolve: Mock) -> None:
        resolve.return_value = ("https://example.com/v1", "secret", "model")
        post.side_effect = requests.Timeout("timeout")

        with self.assertRaises(AppError) as context:
            llm_service.chat_json("system", "user")

        self.assertEqual(context.exception.error, "LLM_TIMEOUT")
        self.assertEqual(context.exception.status_code, 504)

    def test_resume_rate_limit_warning_explains_rule_fallback(self) -> None:
        error = AppError(
            error="LLM_RATE_LIMITED",
            message="LLM 调用额度已用尽或请求过于频繁",
            status_code=503,
        )

        warning = resume_parse_service._build_llm_fallback_warning(error)

        self.assertEqual(
            warning,
            "大模型免费额度已用尽或请求过于频繁，已使用规则解析。",
        )

    @patch("backend.services.resume_parse_service._extract_docx_text")
    @patch("backend.services.resume_parse_service._parse_resume_by_llm")
    def test_resume_rate_limit_returns_rule_profile(self, parse_llm: Mock, extract: Mock) -> None:
        extract.return_value = "张三\n本科计算机专业\n求职意向 后端开发\n技能 Python FastAPI MySQL"
        parse_llm.side_effect = AppError(
            error="LLM_RATE_LIMITED",
            message="LLM 调用额度已用尽或请求过于频繁",
            status_code=503,
        )

        result = resume_parse_service.parse_resume("resume.docx", b"document")

        self.assertEqual(result["source"]["parse_method"], "rule_fallback")
        self.assertIn("Python", result["profile"]["skills"])
        self.assertEqual(
            result["source"]["warnings"],
            ["大模型免费额度已用尽或请求过于频繁，已使用规则解析。"],
        )


if __name__ == "__main__":
    unittest.main()
