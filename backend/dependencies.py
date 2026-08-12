from fastapi import Depends, Header

from backend.errors import AppError
from backend.services import auth_service


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            error="AUTH_REQUIRED",
            message="请先登录",
            status_code=401,
        )
    return auth_service.get_user_from_token(authorization.removeprefix("Bearer ").strip())


def ensure_admin(current_user: dict) -> None:
    if current_user.get("role") != "admin":
        raise AppError(
            error="ADMIN_REQUIRED",
            message="该操作仅管理员可用",
            status_code=403,
        )


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    ensure_admin(current_user)
    return current_user
