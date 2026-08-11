from fastapi import APIRouter, Header

from backend.errors import AppError
from backend.schemas.auth_schema import AuthResponse, LoginRequest, RegisterRequest, UserRead
from backend.services import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> dict:
    return auth_service.register_user(payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> dict:
    return auth_service.login_user(payload)


@router.get("/me", response_model=UserRead)
def me(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            error="AUTH_REQUIRED",
            message="请先登录",
            status_code=401,
        )
    return auth_service.get_user_from_token(authorization.removeprefix("Bearer ").strip())
