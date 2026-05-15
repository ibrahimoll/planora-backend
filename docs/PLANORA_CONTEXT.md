# Planora Backend Context

## Main Idea

Planora is an AI-powered project planning and collaboration system. The backend supports verified users, personal projects, team collaboration, task management, comments, attachments, user profile management, soft account deletion, role-based access control, basic auth rate limiting, protected attachment downloads, and user notifications.

Planned modules will extend the system with team/project invitations, deadline reminders, mentions, progress analytics, activity timeline, AI planning, smart scheduling, risk analysis, AI chat assistant, exportable project reports, admin dashboard APIs, frontend/mobile integration support, tests/security cleanup, Alembic migrations, and Docker deployment polish.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic v2
- Google social login
- SMTP email for verification and password reset codes
- Local upload storage for development

## Latest Verified Status

As of 2026-05-15:

- Step 11 notifications foundation has been implemented and confirmed working after fixing the notification/user relationship and FastAPI query annotation issue.
- The user previously ran the quick pytest check locally and all tests passed before Step 11.
- Step 10 profile management has been implemented in the backend.
- Forgot-password/reset-password email flow was re-tested. The reset code row was created successfully, the SMTP flow worked, and the email was found in the receiver Gmail spam folder. This means the backend flow works; future polish should improve email deliverability.
- Google social-login behavior was updated so new Google accounts must provide a chosen Planora username instead of silently using the email prefix.
- Default profile pictures now use DiceBear initials URLs generated from the user's full name, unless a stored profile picture already exists.
- Account deletion is implemented as a soft delete by setting `users.is_active = false`, not by hard-deleting the user row.

Recent verified additions and security improvements:

- `app/core/rate_limit.py` added a simple in-memory rate limiter.
- Auth routes apply rate limits to register, verify email, resend verification code, forgot password, reset password, login, and Google login.
- Attachment upload security was improved with allowed extensions, 10 MB file-size limit, empty-file rejection, safer filename handling, UUID stored filenames, and local file cleanup on database errors.
- Attachment file access is protected through the attachment router instead of public `StaticFiles` mounting.
- JWT access tokens include `iat` and `token_type`, and decoding requires `sub`, `exp`, `iat`, and `token_type`.
- Basic HTTP security headers were added in `app/main.py`.
- Duplicate root `PLANORA_CONTEXT.md` was removed; the canonical memory file is `docs/PLANORA_CONTEXT.md`.
- Tests added/passing include `tests/test_rate_limit.py` and `tests/test_attachment_security.py`.
- Notifications foundation was added with authenticated user notification listing, unread count, mark-read, mark-all-read, delete, and reusable notification creation service helpers.

## Completed Backend Steps

### Step 1 — Backend Foundation

- FastAPI application created.
- PostgreSQL connection configured.
- Database health route exists.
- Basic HTTP security headers are added in `app/main.py`.

### Step 2 — Authentication

- Registration and login are implemented.
- Email verification is implemented.
- Forgot password / reset password flow is implemented.
- Google login is implemented.
- Apple login is paused/removed because real Apple Sign-In requires a paid Apple Developer setup.
- Protected routes require active verified users.
- No guest access past authentication.
- Basic in-memory rate limiting is implemented for sensitive auth endpoints using `app/core/rate_limit.py`.
- JWT access tokens include `sub`, `exp`, `iat`, and `token_type = access`; decoding validates required claims and token type.
- Normal registration automatically creates a default DiceBear initials `profile_pic` from `full_name`.
- New Google users must provide a Planora `username` in `POST /auth/google`; existing Google-linked users can log in normally without resending a username.
- New Google-created users use a random unusable password hash and `is_email_verified = true`.
- Google-created users can still use forgot/reset password later to set a normal password if needed.

Rate-limited auth endpoints:

- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/resend-verification-code`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /auth/login`
- `POST /auth/google`

Important email note:

- SMTP sending works, but Gmail may place new Planora emails in Spam. For final polish, improve email body formatting, use a clear sender name such as `Planora <planora.verify@gmail.com>`, and eventually use a custom domain with SPF, DKIM, and DMARC.
- Do not keep temporary debug prints that expose verification or reset codes.

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
- Adding a team member supports only `admin` and `member`; `owner` is not assignable through the add-member request.
- Removing a team member also removes that user's project memberships for all projects in that team.

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
- `app/main.py` includes `comment_router`

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

### Step 9 — Attachments

Step 9 is implemented as the attachment/file upload module.

Files:

- `app/models/attachment.py`
- `app/schemas/attachment_schema.py`
- `app/services/attachment_service.py`
- `app/routers/attachment_routes.py`
- `app/main.py` includes `attachment_router`

Storage and serving approach:

- Store files locally under `uploads/attachments/` during development.
- Store metadata in the `attachments` table.
- File URLs use `/uploads/attachments/{stored_file_name}`.
- Files are served through a protected route in `attachment_routes.py`, not through public `StaticFiles` mounting.
- The protected download route checks the current authenticated user before returning a `FileResponse`.
- Personal project files are accessible only to the personal project owner.
- Team project files are accessible only to project members.

Attachment upload security:

- Original filenames are cleaned to prevent path traversal.
- Stored filenames use UUID values.
- Empty files are rejected.
- Files larger than 10 MB are rejected.
- Allowed extensions are `.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.txt`, and `.zip`.
- Local files are deleted if database save fails.
- Local files are deleted when an attachment record is deleted.

Attachment authorization rules:

- Personal project/task attachments are controlled by personal project ownership.
- Team project/task attachments are controlled by project membership.
- Team attachment deletion is allowed for the uploader or project owner/manager.

Attachment endpoints include:

- Personal project attachments.
- Personal task attachments.
- Team project attachments.
- Team task attachments.
- Protected attachment file download.

### Step 10 — User Profile Management

Step 10 is implemented as the profile/account-management module.

Files:

- `app/services/profile_picture_service.py`
- `app/schemas/profile_schema.py`
- `app/services/profile_service.py`
- `app/routers/profile_routes.py`
- `app/main.py` includes `profile_router`

Implemented profile/account features:

- View current user profile.
- Update `username` with uniqueness validation.
- Update `full_name`.
- Update `profile_pic` as a stored string URL/path.
- Change password using old password validation.
- Reject password change when the new password matches the old password.
- Soft-delete/deactivate own account by setting `is_active = false`.
- Account deletion requires confirmation text: `DELETE MY ACCOUNT`.
- Email change is intentionally not implemented yet because it should require a separate re-verification flow.

Profile endpoints:

- `GET /profile`
- `PATCH /profile`
- `PATCH /profile/password`
- `DELETE /profile`

Default profile picture behavior:

- `build_default_profile_pic(full_name)` creates a DiceBear initials URL such as `https://api.dicebear.com/9.x/initials/svg?seed=Ibrahim%20Olleik`.
- Normal registration sets `profile_pic` automatically from the user's `full_name`.
- New Google users also use DiceBear initials as the default profile picture.
- Existing users can update `profile_pic` through `PATCH /profile`.

Google username behavior:

- New Google users must provide `username` in the `POST /auth/google` body.
- If username is missing, backend returns `400` with `Username is required for new Google accounts.`
- If username is already taken, backend returns `409` with `Username is already taken.`
- Existing Google-linked users can log in without providing username again.

Soft account deletion behavior:

- `DELETE /profile` does not hard-delete the `users` row.
- It sets `users.is_active = false`.
- Login and protected routes reject inactive users.
- This avoids breaking project, team, task, comment, attachment, and audit/history references.

### Step 11 — Notifications Foundation

Step 11 is implemented as the notifications module.

Purpose:

- Provide user-facing notifications for future Planora features such as mentions, invitations, deadline reminders, AI suggestions, risk alerts, comments, tasks, teams, and projects.
- Provide a reusable service helper so future modules can create notifications without duplicating logic.

Files:

- `app/models/notification.py`
- `app/schemas/notification_schema.py`
- `app/services/notification_service.py`
- `app/routers/notification_routes.py`
- `app/main.py` imports and includes `notification_router`
- `app/models/user.py` includes the `notifications` relationship

Database table:

- `notifications.notification_id` primary key
- `notifications.user_id` references `users.user_id` with `ON DELETE CASCADE`
- `notifications.title` stores a short notification title
- `notifications.message` stores the notification body
- `notifications.is_read` defaults to `FALSE`
- `notifications.type` supports `task`, `project`, `team`, `comment`, `mention`, `invite`, `deadline`, `ai`, `risk`, and `system`
- `notifications.created_at` stores creation time

Indexes/constraints:

- `idx_notifications_user_id` for user notification lookup
- `idx_notifications_created_at` for sorting/recent notification lookup
- `idx_notifications_unread_by_user` partial index where `is_read = FALSE`
- `chk_notifications_type` keeps notification types controlled

Notification endpoints:

- `GET /notifications` lists the current user's notifications
- `GET /notifications?unread_only=true` lists only unread notifications
- `GET /notifications/unread-count` returns the current user's unread count
- `PATCH /notifications/{notification_id}/read` marks one notification as read
- `PATCH /notifications/read-all` marks all current-user notifications as read
- `DELETE /notifications/{notification_id}` deletes one current-user notification

Authorization rules:

- All notification endpoints require an active verified authenticated user.
- Users can only see, mark, or delete their own notifications.
- A notification ID belonging to another user should not be accessible.

Service helpers:

- `create_notification(...)` creates a notification for a target user.
- `create_notification_from_schema(...)` creates a notification from a schema object.
- `get_my_notifications(...)` lists current-user notifications.
- `get_my_unread_notification_count(...)` counts current-user unread notifications.
- `mark_notification_as_read(...)` marks one notification as read.
- `mark_all_my_notifications_as_read(...)` marks all unread notifications for the current user as read.
- `delete_notification(...)` deletes one notification.

Important implementation fixes from Step 11:

- Initial login crashed with `sqlalchemy.exc.NoForeignKeysError` because SQLAlchemy could not join `notifications` and `users`. The fix was to make `Notification.user_id` use `ForeignKey("users.user_id", ondelete="CASCADE")` and match it with `User.notifications = relationship(back_populates="user")`.
- The live PostgreSQL table also needs a real foreign key from `notifications.user_id` to `users.user_id`; if missing, add it with `ALTER TABLE notifications ADD CONSTRAINT fk_notifications_user_id FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;`.
- SonarLint wanted FastAPI query dependency metadata to use `Annotated`, but FastAPI raised an assertion when the default was placed inside `Query(default=False)`. The correct pattern used is `UnreadOnlyQuery = Annotated[bool, Query()]` and then `unread_only: UnreadOnlyQuery = False` in the route function.
- Notification delete is optional UI cleanup only. Deleting a notification must not delete the real project/task/comment/team data. Permanent project history should be handled later through `activity_logs`, not notifications.

## Planned Backend Roadmap

### Step 12 — Invite System

Purpose: make team/project membership professional by sending invitations instead of directly adding users in every case.

Recommended features:

- Invite user by email or username.
- Accept invitation.
- Reject invitation.
- Expire old invitations.
- Prevent duplicate pending invites.
- Only team owner/admin or project owner/manager can invite, depending on context.
- Create notification for invited users using the Step 11 notification service.

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
- Create notification for each mentioned user using the Step 11 notification service.
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
- Reuse the Step 11 notification service for reminder notifications.

Suggested implementation notes:

- Start with a manual endpoint/service function for development.
- Later move to scheduled jobs using APScheduler, Celery, or another background job system.

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

- `notifications` are user-facing alerts and can be deleted by users.
- `admin_logs` are for admin/system moderation actions.
- `activity_logs` are for normal project/team user activity and should be treated as permanent project history.

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
- Create optional `ai` notifications using the Step 11 notification service.

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
- Notify users/managers when risk is high using the Step 11 notification service.

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

Already started:

- Basic rate-limit tests added and passing.
- Basic attachment security tests added and passing.
- Auth rate limiting added for sensitive auth endpoints.
- Attachment upload and download security improved.
- JWT claim validation improved.
- Basic HTTP security headers added.

Remaining recommended work:

- Add tests for Step 10 profile management and soft account deletion.
- Add tests for Step 11 notification ownership and unread-count behavior.
- Add/clean tests for permissions and collaboration modules.
- Review all ownership/member checks.
- Review upload validation and file size limits again before production.
- Review password/token/security settings.
- Add Alembic migrations.
- Ensure ORM and live database match.

Important user preference:

- Do not provide long PowerShell test scripts by default. Prefer Swagger, Thunder Client, or manual API explanations unless the user explicitly asks for PowerShell.

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
- Step 10 did not require a new table; it uses existing `users` columns, especially `username`, `full_name`, `profile_pic`, `password_hash`, and `is_active`.
- Step 11 uses the existing/planned `notifications` table and requires `notifications.user_id` to have a real FK to `users.user_id`.
- Soft account deletion should remain `is_active = false` for now because hard-deleting users could break project/team/task/comment/attachment/notification history and foreign-key restrictions.

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
python -m pytest -v
```

## Current Next Step

Start Step 12 — Invite System.
