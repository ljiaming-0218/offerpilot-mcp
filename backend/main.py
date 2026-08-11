from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.errors import AppError
from backend.config import settings
from backend.database import init_db, iter_table_names, verify_database

from backend.routers.job_router import router as job_router
from backend.routers.skill_router import router as skill_router
from backend.routers.crawler_router import router as crawler_router
from backend.routers.text2sql_router import router as text2sql_router
from backend.routers.tool_router import router as tool_router
from backend.routers.agent_router import router as agent_router
from backend.routers.profile_router import router as profile_router
from backend.routers.interview_router import router as interview_router
from backend.routers.auth_router import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)
app.include_router(job_router)
app.include_router(skill_router)
app.include_router(crawler_router)
app.include_router(text2sql_router)
app.include_router(tool_router)
app.include_router(agent_router)
app.include_router(profile_router)
app.include_router(interview_router)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "database": "connected" if verify_database() else "unavailable",
        "tables": list(iter_table_names()),
        "llm_configured": settings.llm_configured,
    }


@app.exception_handler(AppError)
def handle_app_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            **exc.details,
        },
    )


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
