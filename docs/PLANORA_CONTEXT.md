# Planora Backend Context

## Main Idea

Planora is an AI-powered project planning and collaboration system. The backend supports verified users, personal projects, team collaboration, task management, comments, attachments, and role-based access control.

Planned modules will extend the system with user profile management, team/project invitations, notifications, deadline reminders, mentions, progress analytics, activity timeline, AI planning, smart scheduling, risk analysis, AI chat assistant, exportable project reports, admin dashboard APIs, frontend/mobile integration support, tests/security cleanup, and Docker deployment polish.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic v2
- Google social login
- Local upload storage for development

## Completed Backend Steps

### Step 1 — Backend Foundation

- FastAPI application created.
- PostgreSQL connection configured.
- Database health route exists.

### Step 2 — Authentication

- Registration and login are implemented.
- Email verification is implemented.
- Forgot password / reset password flow is implemented.
- Google login is implemented.
- Apple login is paused/removed because real Apple Sign-In requires a paid Apple Developer setup.
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

Step 9 is implemented as the attachment/file upload module.

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

## Planned Backend Roadmap

### Step 10 — User Profile Management

Purpose: allow users to view and update their own account/profile details.

Recommended features:

- View current user profile.
- Edit `full_name`.
- Edit `username` with uniqueness validation.
- Update `profile_pic`.
- Change password using old password validation.
- Keep email change separate because changing email should require re-verification.

Suggested endpoints:

- `GET /profile`
- `PATCH /profile`
- `PATCH /profile/password`
- `PATCH /profile/picture`

Suggested files:

- `app/schemas/profile_schema.py`
- `app/services/profile_service.py`
- `app/routers/profile_routes.py`

### Step 11 — Notifications Foundation

Purpose: create the notification system used by mentions, deadline reminders, invitations, AI suggestions, risk alerts, comments, tasks, teams, and projects.

Recommended features:

- List my notifications.
- Mark one notification as read.
- Mark all notifications as read.
- Delete notification if needed.
- Create service helper for other modules to generate notifications.

Suggested endpoints:

- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/read-all`
- `DELETE /notifications/{notification_id}`

Notification types should include:

- `task`
- `project`
- `team`
- `comment`
- `mention`
- `invite`
- `deadline`
- `ai`
- `risk`
- `system`

### Step 12 — Invite System

Purpose: make team/project membership professional by sending invitations instead of directly adding users in every case.

Recommended features:

- Invite user by email or username.
- Accept invitation.
- Reject invitation.
- Expire old invitations.
- Prevent duplicate pending invites.
- Only team owner/admin or project owner/manager can invite, depending on context.
- Create notification for invited users.

Suggested table:

- `invitations`

Suggested columns:

- `invitation_id`
- `invited_by`
- `invited_user_id` nullable if invited by email before account exists
- `email` nullable if invited by existing user
- `team_id` nullable
- `project_id` nullable
- `role`
- `status` with values `pending`, `accepted`, `rejected`, `expired`
- `expires_at`
- `created_at`
- `responded_at`

### Step 13 — Mentions in Comments

Purpose: allow users to mention project/team members inside task comments using `@username`.

Recommended features:

- Parse mentions from comment text.
- Validate that mentioned users are members of the same personal/team project context.
- Support multiple mentions in one comment.
- Prevent mentions of users outside the project.
- Create notification for each mentioned user.
- Link mention notification to the related task/comment.

Suggested table:

- `comment_mentions`

Suggested columns:

- `mention_id`
- `comment_id`
- `mentioned_user_id`
- `mentioned_by`
- `created_at`

### Step 14 — Deadline Reminders

Purpose: notify users about upcoming and overdue tasks/projects.

Recommended features:

- Detect tasks due soon.
- Detect overdue tasks.
- Detect projects near deadline.
- Notify assigned users for task deadlines.
- Notify project owners/managers for project-level deadline risk.
- Avoid duplicate reminders for the same task/date.

Suggested implementation notes:

- Start with a manual endpoint/service function for development.
- Later move to scheduled jobs using APScheduler, Celery, or another background job system.
- Deadline reminders should reuse the notifications service.

Possible notification examples:

- Task due tomorrow.
- Task overdue.
- Project deadline in 3 days.
- Team task overdue and assigned member has not completed it.

### Step 15 — Progress Tracking and Productivity Insights

Purpose: calculate project/user/team progress from task data.

Recommended features:

- Project completion percentage.
- User task completion percentage.
- Team member progress.
- Total tasks vs completed tasks.
- Overdue task count.
- Blocked task count.
- Estimated hours vs actual hours.

Existing table:

- `user_progress`

Notes:

- Decide whether `user_progress` is stored and updated, or calculated dynamically from tasks.
- For FYP simplicity, dynamic calculation can be easier at first; stored summaries can be added later.

### Step 16 — Activity Timeline

Purpose: show a project history/timeline of important actions.

Recommended features:

- Track project creation/update.
- Track task creation/update/status changes.
- Track comments.
- Track attachments.
- Track invitations accepted/rejected.
- Track AI plan generation.
- Track risk analysis generation.
- Show a readable timeline in project detail pages.

Suggested table:

- `activity_logs`

Suggested columns:

- `activity_id`
- `project_id`
- `team_id` nullable
- `actor_id` nullable for system/AI actions
- `activity_type`
- `description`
- `entity_type`
- `entity_id`
- `metadata` JSONB nullable
- `created_at`

Important distinction:

- `admin_logs` are for admin/system moderation actions.
- `activity_logs` are for normal project/team user activity.

### Step 17 — AI Project Planning and Smart Scheduling

Purpose: generate project plans and organize tasks intelligently.

Recommended features:

- Generate task breakdown from a project prompt.
- Suggest milestones.
- Suggest task priorities.
- Estimate task hours.
- Suggest task due dates based on project deadline.
- Allow user to accept/edit generated tasks before saving.
- Store generated plan in `ai_plans`.

Existing table:

- `ai_plans`

### Step 18 — Risk Analysis / Delay Prediction

Purpose: predict whether a project may be delayed and explain why.

Recommended features:

- Calculate risk level: low, medium, high.
- Predict delay days.
- Explain reason for risk.
- Suggest recommendation.
- Store result in `risk_analysis`.
- Notify users/managers when risk is high.

Existing table:

- `risk_analysis`

### Step 19 — AI Chat Assistant

Purpose: allow users to ask AI questions about their project and receive contextual help.

Recommended features:

- Ask questions about project tasks, deadline, progress, and risks.
- Suggest what to do next.
- Explain AI plan steps.
- Help reorganize schedule when the user/team falls behind.
- Store chat history in `chat_messages`.

Existing table:

- `chat_messages`

### Step 20 — Export Project Report

Purpose: generate a professional project report for users, teams, and admin review.

Recommended features:

- Export project summary.
- Include project title, description, deadline, status, and type.
- Include members and roles.
- Include task list and completion status.
- Include comments/attachments summary if needed.
- Include progress statistics.
- Include risk analysis and AI recommendations.
- Include activity timeline summary.

Suggested output formats:

- Start with JSON or HTML summary.
- Later generate PDF for final FYP polish.

### Step 21 — Admin Dashboard APIs and Statistics

Purpose: support the web-based admin dashboard.

Recommended features:

- Admin list users.
- Admin activate/deactivate users.
- Admin view teams/projects/tasks overview.
- Admin view system statistics.
- Admin view activity/admin logs.
- Admin dashboard cards: total users, total projects, total teams, total tasks, active users, completed projects, high-risk projects.

Existing table:

- `admin_logs`

### Step 22 — CORS and Frontend/Mobile Integration Prep

Purpose: prepare the backend for the Flutter mobile app and web admin dashboard.

Recommended features:

- Configure CORS correctly.
- Standardize API response errors.
- Review file URL generation for mobile access.
- Review authentication token flow.
- Prepare API documentation for frontend usage.

### Step 23 — Tests, Permission Checks, Security Cleanup, and Alembic

Purpose: improve reliability and correctness before final delivery.

Recommended work:

- Add/clean tests for permissions and collaboration modules.
- Review all ownership/member checks.
- Review upload validation and file size limits.
- Review password/token/security settings.
- Add Alembic migrations.
- Ensure ORM and live database match.

Important user preference:

- Do not provide long PowerShell test scripts by default. Prefer Swagger/manual API explanations unless the user explicitly asks for PowerShell.

### Step 24 — Docker and Deployment Polish

Purpose: final polish after the backend is stable.

Recommended work:

- Add Dockerfile.
- Add docker-compose for backend + PostgreSQL.
- Add environment variable documentation.
- Prepare production deployment notes.

Important rule:

- Docker should be added later as final polish, not during the unstable core development phase.

## Database Notes

- Existing live database changes should be done using migration/ALTER logic, not by rerunning old create-table scripts.
- ORM models are the current backend source of truth.
- Alembic should be added later.
- If old SQL design files disagree with ORM/backend behavior, treat ORM and current services as the source of truth unless the user explicitly decides otherwise.

## Important Current Database Design Reminders

Current Planora PostgreSQL design includes these main tables:

- `users`
- `teams`
- `team_members`
- `projects`
- `project_members`
- `tasks`
- `attachments`
- `comments`
- `notifications`
- `ai_plans`
- `risk_analysis`
- `user_progress`
- `chat_messages`
- `admin_logs`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

Planned additional tables from the updated roadmap:

- `invitations`
- `comment_mentions`
- `activity_logs`

Optional/polish tables that may be added later:

- `notification_preferences`
- `deadline_reminders` or reminder-tracking table if duplicate reminder prevention requires persisted state
- `project_report_exports` if exported report history is needed

## Local Commands

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\backend
.\venv\Scripts\uvicorn.exe app.main:app --reload
```
