# Planora Backend Context

## Main Idea

Planora is an AI-powered project planning and collaboration system. The backend supports verified users, personal projects, team collaboration, task management, comments, and attachments. Later modules will add AI planning, notifications, progress analytics, risk analysis, chat assistant, admin dashboard, and Docker polish.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic v2
- Google social login
- Local upload storage for development

## Current Backend Steps

### Step 1 — Backend Foundation

- FastAPI application created.
- PostgreSQL connection configured.
- Database health route exists.

### Step 2 — Authentication

- Registration and login are implemented.
- Email verification is implemented.
- Reset flow is implemented.
- Google login is implemented.
- Apple login is paused/removed.
- Protected routes require active verified users.
- No guest access past authentication.

### Step 3 — Personal Projects

- Users can create, list, view, update, and delete personal projects.
- Personal projects use `project_type = personal` and `team_id = NULL`.

### Step 4 — Personal Tasks

- Users can create, list, view, update, and delete tasks inside their own personal projects.
- Task completion updates `completed_at` automatically.

### Step 5 — Teams

- Users can create teams.
- Team creator becomes owner.
- Team roles: owner, admin, member.
- Team owners/admins manage members.

### Step 6 — Team Projects

- Team owners/admins can create team projects.
- Team projects use `project_type = team` and require `team_id`.
- Team members are copied into project memberships.
- Project roles: owner, manager, member.

### Step 7 — Team Project Tasks

- Project owners/managers can create, update, assign, and delete team tasks.
- Assigned members can update only their own task status and actual hours.
- Assignees must be project members.

### Step 8 — Task Comments

Step 8 is implemented as the task comments module.

Files:

- `app/models/comment.py`
- `app/schemas/comment_schema.py`
- `app/services/comment_service.py`
- `app/routers/comment_routes.py`
- `app/main.py` must include `comment_router`

Database table:

- `comments.comment_id` primary key
- `comments.task_id` references `tasks.task_id`
- `comments.user_id` references `users.user_id`
- `comments.comment_text` stores the message
- `comments.created_at` stores creation time

Personal task comment endpoints:

- `POST /projects/{project_id}/tasks/{task_id}/comments`
- `GET /projects/{project_id}/tasks/{task_id}/comments`
- `GET /projects/{project_id}/tasks/{task_id}/comments/{comment_id}`
- `PATCH /projects/{project_id}/tasks/{task_id}/comments/{comment_id}`
- `DELETE /projects/{project_id}/tasks/{task_id}/comments/{comment_id}`

Team task comment endpoints:

- `POST /teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments`
- `GET /teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments`
- `GET /teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}`
- `PATCH /teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}`
- `DELETE /teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}`

Step 8 authorization rules:

- Personal comments are only accessible by the personal project owner.
- Team comments are only accessible by project members.
- Team comment update/delete is allowed for the comment author or a project owner/manager.
- Users outside the project must not access comments.

Important Step 8 reminder:

If comments do not appear in Swagger, make sure `app/main.py` contains:

```python
from app.routers.comment_routes import router as comment_router
app.include_router(comment_router)
```

### Step 9 — Attachments

Step 9 is the attachment/file upload module.

Files:

- `app/models/attachment.py`
- `app/schemas/attachment_schema.py`
- `app/services/attachment_service.py`
- `app/routers/attachment_routes.py`
- `app/main.py` must include `attachment_router`

Storage approach:

- Store files locally under `uploads/attachments/` during development.
- Store metadata in the `attachments` table.
- Serve uploads through `/uploads` using FastAPI `StaticFiles`.

Attachment authorization rules:

- Personal project/task attachments are controlled by personal project ownership.
- Team project/task attachments are controlled by project membership.
- Team attachment deletion is allowed for the uploader or project owner/manager.

## Database Notes

- Existing live database changes should be done using migration/ALTER logic, not by rerunning old create-table scripts.
- ORM models are the current backend source of truth.
- Alembic should be added later.

## Deferred Work

- Notifications
- Progress tracking
- AI planning
- Risk analysis
- AI chat assistant
- Admin dashboard
- CORS setup before frontend integration
- Tests for permissions and collaboration modules
- Docker later after the backend is stable

## Local Commands

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\backend
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\uvicorn.exe app.main:app --reload
```
