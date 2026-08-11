import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from sqlalchemy.exc import IntegrityError

from backend.config import settings
from backend.errors import AppError
from backend.repositories import auth_repository
from backend.schemas.auth_schema import LoginRequest, RegisterRequest


TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60


def register_user(payload: RegisterRequest) -> dict[str, Any]:
    role = "admin" if auth_repository.count_users() == 0 else "user"
    try:
        user = auth_repository.create_user(
            username=payload.username,
            password_hash=_hash_password(payload.password),
            role=role,
            display_name=payload.display_name,
        )
    except IntegrityError as exc:
        raise AppError(
            error="USERNAME_EXISTS",
            message="用户名已存在",
            status_code=409,
        ) from exc

    return {
        "token": _create_token(user),
        "user": user,
    }


def login_user(payload: LoginRequest) -> dict[str, Any]:
    user = auth_repository.get_user_by_username(payload.username)
    if user is None or not _verify_password(payload.password, user["password_hash"]):
        raise AppError(
            error="INVALID_CREDENTIALS",
            message="用户名或密码错误",
            status_code=401,
        )

    safe_user = _safe_user(user)
    return {
        "token": _create_token(safe_user),
        "user": safe_user,
    }


def get_user_from_token(token: str) -> dict[str, Any]:
    payload = _verify_token(token)
    user = auth_repository.get_user_by_id(int(payload["user_id"]))
    if user is None:
        raise AppError(
            error="USER_NOT_FOUND",
            message="登录用户不存在",
            status_code=401,
        )
    return user


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return hmac.compare_digest(expected, digest)


def _create_token(user: dict[str, Any]) -> str:
    payload = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_b64 = _b64encode(payload_text.encode("utf-8"))
    signature = _sign(payload_b64)
    return f"{payload_b64}.{signature}"


def _verify_token(token: str) -> dict[str, Any]:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise _invalid_token_error() from exc

    if not hmac.compare_digest(_sign(payload_b64), signature):
        raise _invalid_token_error()

    try:
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise _invalid_token_error() from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise AppError(
            error="TOKEN_EXPIRED",
            message="登录已过期，请重新登录",
            status_code=401,
        )
    return payload


def _sign(payload_b64: str) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _invalid_token_error() -> AppError:
    return AppError(
        error="INVALID_TOKEN",
        message="登录凭证无效，请重新登录",
        status_code=401,
    )


def _safe_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name"),
        "created_at": user.get("created_at"),
    }
