# Planora Backend Context

## Purpose

Planora is an AI-powered project planning and collaboration backend. The current backend focuses on authentication, verified user access, personal projects, teams, team projects, task assignment, and the next collaboration modules. AI planning, attachments, comments, notifications, progress analytics, chat, and admin tooling are part of the planned Planora roadmap.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic v2
- JWT bearer authentication
- SMTP email delivery
- Google ID token login

## Repository State Checked

Repository: `ibrahimoll/planora-backend`

Default branch: `main`

Important checked files:

- `app/main.py`
- `app/models/user.py`
- `app/models/project.py`
- `app/models/task.py`
- `app/models/team.py`
- `app/models/project_member.py`
- `app/routers/team_task_routes.py`
- `app/services/project_service.py`
- `app/services/task_service.py`
- `requirements.txt`

Current `app/main.py` includes routers for:

- Auth
- Personal projects
- Personal tasks
- Teams
- Team projects
- Team project tasks

At the time this context was updated, the GitHub `main` branch did not show comment route/model/service files included in `app/main.py`. If Step 8 comments exist locally, push them before relying on GitHub `main` as the full source of truth.

## Completed / Current Development Steps

### Step 1 — Backend foundation

- FastAPI app created.
- PostgreSQL connection configured through SQLAlchemy session.
- `/health/db` exists for database connection checking.

### Step 2 — Authentication

- Normal registration/login with email and password.
- Email verification with 6-digit code.
- Resend verification code.
- Forgot password/reset password flow.
- Password strength validation.
- JWT access token creation and decoding.
- Protected current-user dependency.
- `/auth/me` protected route.
- Google social login.
- Apple login removed/paused because real Apple Sign-In requires paid Apple Developer setup.

### Step 3 — Personal projects

- Users can create/list/get/update/delete personal projects.
- Personal projects use `project_type = 'personal'` and `team_id IS NULL`.
- Protected routes require active, email-verified users.

### Step 4 — Personal tasks

- Users can create/list/get/update/delete tasks inside their own personal projects.
- Personal tasks are assigned to the current user.
- Task status update controls `completed_at` automatically.

### Step 5 — Teams

- Users can create teams.
- Creator becomes team owner.
- Team member roles: `owner`, `admin`, `member`.
- Add-member request supports `admin` and `member`, not owner.
- Team owners/admins manage team details and members.
- Removing a team member should also remove their project memberships for team projects.

### Step 6 — Team projects

- Team owners/admins can create team projects.
- Team projects use `project_type = 'team'` and require `team_id`.
- Team members are copied into `project_members` for the new project.
- Team/project permissions use `ProjectMember` records.

### Step 7 — Team project tasks

- Project owners/managers can create, update, assign, and delete team project tasks.
- Assigned project members can update only their own task status and actual hours.
- Assignees must be members of the project.

### Step 8 — Task comments

- Intended module: task comments for personal and team tasks.
- Comments should link to `tasks.task_id` and `users.user_id`.
- Access must be inherited from task/project access rules.
- If Step 8 was implemented locally, make sure the files are pushed and `app/main.py` includes the comment router.

### Step 9 — Attachments / file uploads

Step 9 should implement attachments for personal and team project tasks/projects.

Recommended first backend scope:

- Create `Attachment` SQLAlchemy model.
- Create `attachment_schema.py`.
- Create `attachment_service.py`.
- Create `attachment_routes.py`.
- Include the attachment router in `app/main.py`.
- Store uploaded files locally under `uploads/attachments/` for FYP development.
- Store metadata in the `attachments` table.
- Keep real cloud storage such as S3/Supabase Storage/Firebase Storage deferred until the core system is stable.

Recommended endpoint shape:

- `POST /projects/{project_id}/attachments`
- `GET /projects/{project_id}/attachments`
- `DELETE /projects/{project_id}/attachments/{attachment_id}`
- `POST /projects/{project_id}/tasks/{task_id}/attachments`
- `GET /projects/{project_id}/tasks/{task_id}/attachments`
- `DELETE /projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}`
- `POST /teams/{team_id}/projects/{project_id}/attachments`
- `GET /teams/{team_id}/projects/{project_id}/attachments`
- `DELETE /teams/{team_id}/projects/{project_id}/attachments/{attachment_id}`
- `POST /teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments`
- `GET /teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments`
- `DELETE /teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}`

Authorization rules for Step 9:

- Personal project attachments: only the owner can create/list/delete.
- Personal task attachments: only the owner of the personal project/task can create/list/delete.
- Team project/task attachments: any project member can create/list.
- Team project/task attachment delete: uploader OR project owner/manager can delete.
- Never allow users outside the project to access attachment metadata or file URLs.

Recommended attachment table shape:

```sql
CREATE TABLE attachments (
    attachment_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL,
    task_id BIGINT NULL,
    uploaded_by BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(100),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_attachments_project
        FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_attachments_task
        FOREIGN KEY (task_id)
        REFERENCES tasks(task_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_attachments_uploaded_by
        FOREIGN KEY (uploaded_by)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_attachments_project_id ON attachments(project_id);
CREATE INDEX idx_attachments_task_id ON attachments(task_id);
CREATE INDEX idx_attachments_uploaded_by ON attachments(uploaded_by);
```

If the existing live database already has the table, do not rerun `CREATE TABLE`; use `ALTER TABLE` migrations only.

## Important Security Rules

- Do not commit or expose `.env` values.
- Keep configuration in `app/core/config.py`.
- Keep protected routes behind `get_current_active_verified_user`.
- Do not add guest access beyond authentication.
- Google login should read the profile image from the Google `picture` claim.
- Attachment upload must validate file size and allowed file extensions before saving.
- Use safe generated filenames on disk; never trust the uploaded filename as the storage filename.
- Store original filename only as metadata.

## Authorization Model

- Team owners can delete teams and update member roles.
- Team owners and admins can manage team details and members.
- Team members can view teams they belong to.
- Team project access is based on `ProjectMember` records.
- Project owners and managers can create, update, assign, and delete team project tasks.
- Assigned project members can update only their own task status and actual hours.
- Attachment metadata/file URLs must only be visible to users with access to the related project/task.

## Database Notes

- The old SQL design file is a reference only if it exists locally; it may not represent the live PostgreSQL database if ALTER TABLE migrations were already applied.
- The ORM models are the current backend source of truth for application behavior.
- A future Alembic migration setup should replace manual schema drift management.
- Existing schema mistakes must be fixed using `ALTER TABLE`, not by editing and rerunning old `CREATE TABLE` SQL.

## Known Deferred Work

- Add rate limiting and cooldowns for login, verification, resend verification, forgot password, and reset password flows.
- Add CORS configuration before frontend or admin dashboard integration.
- Add tests for auth, email rollback behavior, team/project authorization, project membership synchronization, task permissions, comments, and attachments.
- Reconcile any old SQL schema file with the ORM and live database migrations.
- Add structured logging around auth failures, email failures, permission denials, and upload failures.
- Add AI plans, notifications, progress tracking, chat assistant, risk analysis, and admin dashboard.
- Add Docker later as final polish after the core backend is stable.

## Local Backend Commands

Use local terminal commands only when needed. Prefer Swagger/manual API checks for development if terminal test scripts are causing trouble.

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\backend
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\uvicorn.exe app.main:app --reload
```
