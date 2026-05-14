from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.session import test_database_connection
from app.routers.auth import router as auth_router
from app.routers.project_routes import router as project_router
from app.routers.task_routes import router as task_router
from app.routers.team_routes import router as team_router
from app.routers.team_project_routes import router as team_project_router
from app.routers.team_task_routes import router as team_task_router
from app.routers.attachment_routes import router as attachment_router

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
ATTACHMENTS_DIR = UPLOADS_DIR / "attachments"

ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Planora API",
    description="Backend API for the Planora AI project planning and colab system",
    version="1.0.0",
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads",
)

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(team_router)
app.include_router(team_project_router)
app.include_router(team_task_router)
app.include_router(attachment_router)


@app.get("/")
def root():
    return {
        "message": "Planora backend is running"
    }


@app.get("/health/db")
def database_health_check():
    result = test_database_connection()

    return {
        "message": "Database connection successful",
        "result": result,
    }