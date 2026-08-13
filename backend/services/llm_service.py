import json
import re
from typing import Any

import requests

from backend.config import settings
from backend.errors import AppError


def chat_json(system_prompt: str, user_prompt: str, timeout: int = 40) -> dict[str, Any]:
    base_url, api_key, model = _resolve_llm_config()
    url = f"{base_url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise AppError(
            error="LLM_TIMEOUT",
            message="LLM 响应超时",
            status_code=504,
        ) from exc
    except requests.RequestException as exc:
        raise AppError(
            error="LLM_UNAVAILABLE",
            message="无法连接 LLM 服务",
            status_code=502,
        ) from exc

    if response.status_code >= 400:
        raise _build_request_error(response)

    try:
        data = response.json()
    except ValueError as exc:
        raise AppError(
            error="LLM_RESPONSE_INVALID",
            message="LLM 返回了无法解析的响应",
            status_code=502,
        ) from exc
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return _parse_json_content(content)


def _build_request_error(response: requests.Response) -> AppError:
    status = response.status_code
    provider_message = _read_provider_message(response)
    details = {"provider_status": status}
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        details["retry_after"] = retry_after
    if provider_message:
        details["provider_message"] = provider_message[:300]

    if status == 429:
        return AppError(
            error="LLM_RATE_LIMITED",
            message="LLM 调用额度已用尽或请求过于频繁",
            status_code=503,
            **details,
        )
    if status in {401, 403}:
        return AppError(
            error="LLM_AUTH_FAILED",
            message="LLM API Key 无效或无权访问当前模型",
            status_code=502,
            **details,
        )
    if status == 402:
        return AppError(
            error="LLM_PAYMENT_REQUIRED",
            message="LLM 账户余额不足或需要开通付费额度",
            status_code=503,
            **details,
        )
    if status >= 500:
        return AppError(
            error="LLM_PROVIDER_UNAVAILABLE",
            message="LLM 服务暂时不可用",
            status_code=502,
            **details,
        )
    return AppError(
        error="LLM_REQUEST_FAILED",
        message="LLM 请求未被服务商接受",
        status_code=502,
        **details,
    )


def _read_provider_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "").strip()
    if isinstance(error, str):
        return error.strip()
    return str(payload.get("message") or "").strip()


def is_llm_available() -> bool:
    try:
        _resolve_llm_config()
        return True
    except AppError:
        return False


def _resolve_llm_config() -> tuple[str, str, str]:
    if settings.openrouter_api_key:
        return (
            settings.openrouter_base_url or "https://openrouter.ai/api/v1",
            settings.openrouter_api_key,
            settings.openrouter_model or settings.llm_model or "openai/gpt-4o-mini",
        )

    if settings.llm_api_key:
        if not settings.llm_base_url:
            raise AppError(
                error="LLM_BASE_URL_NOT_CONFIGURED",
                message="已配置 LLM_API_KEY，但缺少 LLM_BASE_URL",
                status_code=500,
            )
        return (
            settings.llm_base_url,
            settings.llm_api_key,
            settings.llm_model or "gpt-4o-mini",
        )

    raise AppError(
        error="LLM_NOT_CONFIGURED",
        message="未配置 LLM API Key",
        status_code=500,
    )


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AppError(
            error="LLM_JSON_PARSE_FAILED",
            message="LLM 未返回合法 JSON",
            status_code=502,
            raw_output=content[:800],
        ) from exc

    if not isinstance(parsed, dict):
        raise AppError(
            error="LLM_JSON_TYPE_INVALID",
            message="LLM JSON 顶层必须是对象",
            status_code=502,
        )

    return parsed
