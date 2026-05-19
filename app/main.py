from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.session import test_database_connection
from app.routers.auth import router as auth_router
from app.routers.project_routes import router as project_router
from app.routers.task_routes import router as task_router
from app.routers.team_routes import router as team_router
from app.routers.team_project_routes import router as team_project_router
from app.routers.team_task_routes import router as team_task_router
from app.routers.comment_routes import router as comment_router
from app.routers.attachment_routes import router as attachment_router
from app.routers.profile_routes import router as profile_router
from app.routers.notification_routes import router as notification_router
from app.routers.invitation_routes import router as invitation_router
from app.routers.deadline_reminder_routes import router as deadline_reminder_router
from app.routers.report_routes import router as report_router
from app.routers.activity_log_routes import router as activity_log_router
from app.routers.progress_routes import router as progress_router
from app.routers.productivity_insight_routes import router as productivity_insight_router
from app.routers.ai_plan_routes import router as ai_plan_router
from app.routers.risk_analysis_routes import router as risk_analysis_router
from app.routers.smart_schedule_routes import router as smart_schedule_router
from app.routers.admin_dashboard_routes import router as admin_dashboard_router
from app.routers.admin_user_management_routes import router as admin_user_management_router
from app.routers.admin_project_oversight_routes import router as admin_project_oversight_router
from app.routers.admin_task_oversight_routes import router as admin_task_oversight_router
from app.routers.admin_risk_report_routes import router as admin_risk_report_router
from app.routers.ai_chat_routes import router as ai_chat_router
from app.routers.push_notification_routes import router as push_notification_router
from app.services.deadline_reminder_scheduler import (
    start_deadline_reminder_scheduler,
    stop_deadline_reminder_scheduler,
)

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_deadline_reminder_scheduler()

    try:
        yield
    finally:
        await stop_deadline_reminder_scheduler()


app = FastAPI(
    title="Planora API",
    description="Backend API for the Planora AI project planning and collaboration system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
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
app.include_router(profile_router)
app.include_router(notification_router)
app.include_router(invitation_router)
app.include_router(deadline_reminder_router)
app.include_router(report_router)
app.include_router(activity_log_router)
app.include_router(progress_router)
app.include_router(productivity_insight_router)
app.include_router(ai_plan_router)
app.include_router(risk_analysis_router)
app.include_router(smart_schedule_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_user_management_router)
app.include_router(admin_project_oversight_router)
app.include_router(admin_task_oversight_router)
app.include_router(admin_risk_report_router)
app.include_router(ai_chat_router)
app.include_router(push_notification_router)

@app.get("/")
def root():
    return {"message": "Planora backend is running"}

@app.get("/health/db")
def database_health_check():
    result = test_database_connection()
    return {"message": "Database connection successful", "result": result}