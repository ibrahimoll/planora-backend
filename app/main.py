from fastapi import FastAPI

from app.db.session import test_database_connection
from app.routers.auth import router as auth_router
from app.routers.project_routes import router as project_router
from app.routers.task_routes import router as task_router
from app.routers.team_routes import router as team_router
from app.routers.team_project_routes import router as team_project_router
from app.routers.team_task_routes import router as team_task_router
from app.routers.comment_routes import router as comment_router
from app.routers.attachment_routes import router as attachment_router

app = FastAPI(
    title="Planora API",
    description="Backend API for the Planora AI project planning and colab system",
    version="1.0.0",
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(team_router)
app.include_router(team_project_router)
app.include_router(team_task_router)
app.include_router(comment_router)
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
