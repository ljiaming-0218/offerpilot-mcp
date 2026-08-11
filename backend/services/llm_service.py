import json
import re
from typing import Any

import requests

from backend.config import settings
from backend.errors import AppError


def chat_json(system_prompt: str, user_prompt: str, timeout: int = 40) -> dict[str, Any]:
    base_url, api_key, model = _resolve_llm_config()
    url = f"{base_url.rstrip('/')}/chat/completions"

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

    if response.status_code >= 400:
        raise AppError(
            error="LLM_REQUEST_FAILED",
            message="LLM 调用失败",
            status_code=502,
            reason=response.text[:500],
        )

    data = response.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return _parse_json_content(content)


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
