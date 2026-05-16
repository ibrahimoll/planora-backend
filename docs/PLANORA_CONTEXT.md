# Planora Backend Context

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.
- AI planning, smart scheduling, risk prediction, productivity insights, and AI chat assistant planned for later phases.

The backend currently uses FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, Google social login, SMTP email for verification/reset flows, and local file storage for development.

Firebase decision:

- Firebase Cloud Messaging will be used later for real mobile push notifications.
- Firebase Storage will be used later for attachments/files.
- For now, notifications are stored as in-app rows in the `notifications` table.
- For now, attachments are stored locally during backend development.

## Current Verified Status — 2026-05-16

Completed backend steps:

1. Backend foundation.
2. Authentication.
3. Personal projects.
4. Personal tasks.
5. Teams.
6. Team projects.
7. Team project tasks.
8. Task comments.
9. Attachments.
10. User profile management.
11. Notifications foundation.
12. Invitation system.
13. Mentions in comments.
14. Deadline reminders.
15. Export project report.
16. Activity timeline / activity logs.
17. Progress tracking and productivity insights.
18. Project member role update endpoint.

Latest confirmed regression result:

- `56 passed`
- Command used by the user: `python -m pytest -x -v`
- Test database requirement: `TEST_DATABASE_URL` must point to `planora_test_db`, not the normal development database.

Important current notes:

- Google-created accounts cannot use Swagger password authorization unless they set a Planora password through forgot/reset password.
- Google-created users normally authenticate through `POST /auth/google` and receive a Planora JWT.
- Protected routes require active and email-verified Planora users.
- Missing/invalid bearer tokens return `401 Unauthorized` through the auth dependency.
- Authenticated users who are not allowed to perform an action should receive `403 Forbidden`.
- `notifications.type` must allow: `task`, `project`, `team`, `comment`, `mention`, `invite`, `deadline`, `ai`, `risk`, `system`.
- If invitation, mention, or deadline notifications fail when inserting notification types, fix the live PostgreSQL notification check constraint.
- Team roles and project roles are separate.
- Updating `team_members.role` does not automatically update `project_members.role`.
- A team `admin` is not automatically a project `manager` for existing projects.
- Project member role update is now implemented through the Step 18 endpoint.
- Code cleanup note: after Step 18, `app/routers/team_project_routes.py` may contain duplicate import blocks. Tests pass, but the imports should be cleaned in a later polish pass.

## Regression Testing Status — 2026-05-16

A pytest regression suite exists in the `tests/` folder and should be used after every backend feature step.

Latest full regression result:

- 56 tests collected.
- 56 tests passed.
- Command used: `python -m pytest -x -v`.

Current test coverage includes:

- Authentication registration, weak-password rejection, verified-login behavior, `/auth/me`, duplicate email rejection, and missing-token protection.
- Personal project CRUD and cross-user access protection.
- Personal task CRUD and completed-task timestamp behavior.
- Team creation, owner membership, adding members, and updating team member roles.
- Team project creation and team task update flow.
- Project member role update permissions and validation.
- Personal task comments CRUD.
- Team comment mentions creating unread `mention` notifications.
- Notification unread count and mark-as-read behavior.
- Team invitation accept and reject flows.
- Profile route availability.
- Attachment route protection and attachment filename/path-traversal security helpers.
- Rate-limit blocking behavior.
- Deadline reminder admin-only scan permissions.
- Deadline reminder due-soon and overdue notification creation.
- Deadline reminder duplicate-prevention behavior.
- Deadline reminder history listing through `/deadline-reminders/me`.
- Deadline scan ignoring completed tasks.
- Export project report success for owner.
- Export project report cross-user protection.
- Export project report missing-token protection.
- Activity log listing, ordering, event-type filtering, pagination, project isolation, personal-project protection, team-member access, and unauthenticated access protection.
- Progress tracking for personal projects and team projects, cross-user protection, and missing-token protection.

Important test setup notes:

- Tests use `TEST_DATABASE_URL`, not the normal development `DATABASE_URL`.
- The current local test database is `planora_test_db`.
- `tests/conftest.py` overrides FastAPI `get_db()` to use the test database.
- `tests/conftest.py` disables real outbound verification/password-reset emails during tests.
- `tests/conftest.py` imports the FastAPI instance as `fastapi_app` to avoid shadowing it with the Python `app` package.
- The test database schema is dropped and recreated by pytest, so never point `TEST_DATABASE_URL` to `planora_db`.

Current pytest-related files:

- `tests/conftest.py`
- `tests/__init__.py`
- `tests/test_01_auth_api.py`
- `tests/test_02_personal_projects_tasks_api.py`
- `tests/test_03_teams_team_projects_tasks_api.py`
- `tests/test_04_comments_mentions_notifications_api.py`
- `tests/test_05_invitations_api.py`
- `tests/test_06_profile_attachments_smoke_api.py`
- `tests/test_07_deadline_reminders_api.py`
- `tests/test_09_progress_api.py`
- `tests/test_10_project_member_roles_api.py`
- `tests/test_activity_log_routes.py`
- `tests/test_report_routes.py`
- `tests/test_attachment_security.py`
- `tests/test_rate_limit.py`

Standard local pytest command pattern:

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
```

Useful local commands:

```powershell
python -m pytest --collect-only -q
python -m pytest --cov=app --cov-report=term-missing
python -m compileall app tests
python -m pip check
```

Future testing rule:

- Every new backend feature step should include pytest tests in the same style before the step is considered fully done.
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions for permissions, success cases, and edge cases.
- Keep using `python -m pytest -x -v` as the first full regression check.
- User prefers pytest tests and does not want long PowerShell API scripts by default.

## Step 12 — Invitation System Completed

Step 12 uses the existing `invitations` table. Do not create a separate `team_invitations` table.

Current invitation flow:

- Team owner/admin invites by Planora username.
- Backend resolves `users.username` to `invited_user_id`.
- `email` stays `NULL` for current registered-user app flow.
- Backend creates a pending row in `invitations`.
- Backend creates an in-app notification with `type = invite`.
- Invited user can list pending invitations.
- Invited user can accept or reject.
- Accepting adds the user to `team_members`.
- Accepting also adds the user to existing team projects as project `member`, unless already present.

Step 12 files:

- `app/models/invitation.py`
- `app/schemas/invitation_schema.py`
- `app/services/invitation_service.py`
- `app/routers/invitation_routes.py`
- `app/main.py` includes `invitation_router`.

Step 12 endpoints:

- `POST /teams/{team_id}/invitations`
- `GET /invitations/me`
- `POST /invitations/{invitation_id}/accept`
- `POST /invitations/{invitation_id}/reject`

Current invitation table columns:

- `invitation_id`
- `invited_by`
- `invited_user_id`
- `email`
- `team_id`
- `project_id`
- `role`
- `status`
- `expires_at`
- `created_at`
- `responded_at`

Invitation status values:

- `pending`
- `accepted`
- `rejected`
- `expired`

Invitation role values:

- `admin`
- `manager`
- `member`

Team invitation role rule:

- Team invitations should only use `admin` or `member`.
- `manager` is for project-level invitations later.
- `owner` should not be assignable through normal invitations.

Duplicate invite rule:

- Prevent duplicate pending invitations for the same team and same invited user.

Recommended partial unique index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_invitations_pending_team_user
ON invitations(team_id, invited_user_id)
WHERE status = 'pending' AND project_id IS NULL;
```

Notification constraint fix if needed:

```sql
ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS fk_notifications_type;

ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS chk_notifications_type;

ALTER TABLE notifications
ADD CONSTRAINT chk_notifications_type
CHECK (
    type IN (
        'task',
        'project',
        'team',
        'comment',
        'mention',
        'invite',
        'deadline',
        'ai',
        'risk',
        'system'
    )
);
```

## Step 13 — Mentions in Comments Completed

Step 13 adds `@username` mentions inside task comments.

Current mention behavior:

- User writes a comment containing one or more usernames, for example `@ali`.
- Backend parses mentioned usernames from `comment_text`.
- Backend ignores duplicate usernames inside the same comment.
- Backend checks that the username exists and belongs to the same project before creating a mention.
- For team projects, only project members can be mentioned.
- For personal projects, the system should not notify random outside users.
- Backend saves mention rows in `comment_mentions`.
- Backend creates in-app notifications with `type = mention`.
- The author should not receive a mention notification for mentioning themselves.
- When a comment is updated, old mention rows are replaced based on the new comment text.
- When a comment is deleted, related mention rows are deleted through cascade.

Step 13 files:

- `app/models/comment_mention.py`
- Updated `app/models/comment.py`
- Updated `app/models/user.py`
- Updated `app/models/__init__.py`
- Updated `app/services/comment_service.py`
- Updated `app/routers/comment_routes.py`

Current `comment_mentions` table columns:

- `mention_id`
- `comment_id`
- `project_id`
- `task_id`
- `mentioned_user_id`
- `mentioned_by`
- `created_at`

Important constraints/indexes:

- `comment_id` references `comments(comment_id)` with `ON DELETE CASCADE`.
- `project_id` references `projects(project_id)` with `ON DELETE CASCADE`.
- `task_id` references `tasks(task_id)` with `ON DELETE CASCADE`.
- `mentioned_user_id` references `users(user_id)` with `ON DELETE CASCADE`.
- `mentioned_by` references `users(user_id)` with `ON DELETE CASCADE`.
- Unique rule: one mentioned user should appear only once per comment.
- Indexes should exist for `comment_id`, `project_id`, `task_id`, `mentioned_user_id`, and `mentioned_by`.

## Step 14 — Deadline Reminders Completed

Step 14 adds backend deadline reminder scanning and in-app deadline notifications.

Current deadline reminder behavior:

- Admins can manually run a deadline scan.
- Normal users cannot run the scan.
- Incomplete assigned tasks with `due_date` inside the scan window create `due_soon` reminders.
- Incomplete assigned tasks with `due_date` in the past create `overdue` reminders when `include_overdue = true`.
- Completed tasks are ignored.
- Tasks without assignees or without due dates are ignored.
- Duplicate reminders are prevented by the `deadline_reminders` table unique rule.
- Reminder creation also creates an in-app notification with `type = deadline`.
- Users can list their own reminder history.

Step 14 files:

- `app/models/deadline_reminder.py`
- `app/schemas/deadline_reminder_schema.py`
- `app/services/deadline_reminder_service.py`
- `app/routers/deadline_reminder_routes.py`
- Updated `app/models/task.py`
- Updated `app/models/project.py`
- Updated `app/models/user.py`
- Updated `app/models/__init__.py`
- Updated `app/main.py` to include `deadline_reminder_router`.
- `tests/test_07_deadline_reminders_api.py`

Step 14 endpoints:

- `POST /deadline-reminders/run`
- `GET /deadline-reminders/me`

Current `deadline_reminders` table columns:

- `reminder_id`
- `task_id`
- `project_id`
- `user_id`
- `reminder_type`
- `due_date_snapshot`
- `generated_at`

Deadline reminder type values:

- `due_soon`
- `overdue`

Important constraints/indexes:

- `task_id` references `tasks(task_id)` with `ON DELETE CASCADE`.
- `project_id` references `projects(project_id)` with `ON DELETE CASCADE`.
- `user_id` references `users(user_id)` with `ON DELETE CASCADE`.
- `reminder_type` must be `due_soon` or `overdue`.
- Unique rule: one reminder per `(task_id, user_id, reminder_type, due_date_snapshot)`.
- Indexes should exist for `task_id`, `project_id`, `user_id`, `reminder_type`, and `generated_at`.

## Step 15 — Export Project Report Completed

Step 15 adds an export-ready JSON project report endpoint. It does not add a new database table. It reads from existing Planora tables and returns structured project, progress, task, member, hours, and activity summary data.

Step 15 endpoint:

- `GET /reports/projects/{project_id}`

Step 15 files:

- `app/schemas/report_schema.py`
- `app/services/report_service.py`
- `app/routers/report_routes.py`
- Updated `app/main.py` to include `report_router`.
- `tests/test_report_routes.py`

Tables used by Step 15:

- `projects` for title, description, status, type, deadline, created/updated timestamps.
- `tasks` for task list, task status counts, priority counts, completion percentage, overdue count, estimated hours, and actual hours.
- `project_members` and `users` for team project member details.
- `comments` for project comment count.
- `attachments` for project attachment count.
- `deadline_reminders` for project deadline reminder count.

Current report behavior:

- Personal project owner can export the report.
- Team project members can export the report.
- A user cannot export another user's personal project report.
- Missing or invalid bearer token returns `401 Unauthorized`.
- Unauthorized project access returns `404 Project not found` to avoid leaking project existence.
- The endpoint returns JSON only for now; frontend/mobile can later convert it to PDF or display it as a report screen.

Current report response sections:

- `generated_at`
- `project`
- `progress`
- `task_status_counts`
- `task_priority_counts`
- `hours`
- `activity`
- `members`
- `tasks`

Important Step 15 code fixes applied:

- `ReportProjectStatus(project.status)` and `ReportProjectType(project.project_type)` are used to satisfy Pylance enum type checking.
- `is_task_overdue()` and `build_task_report_item()` helper functions reduce SonarLint cognitive complexity in `generate_project_report()`.
- `project.py` uses `CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"` to avoid duplicate string warnings.
- `tests/test_report_routes.py` expects `401` for missing token and uses `pytest.approx(0.0)` for float comparison.

No SQL migration is required for Step 15.

## Step 16 — Activity Timeline / Activity Logs Completed

Step 16 adds project activity logs for important project events.

Step 16 endpoint:

- `GET /projects/{project_id}/activity`

Step 16 files include:

- `app/models/activity_log.py`
- `app/schemas/activity_log_schema.py`
- `app/services/activity_log_service.py`
- `app/routers/activity_log_routes.py`
- Updated project, task, comment, attachment, and deadline reminder flows to create activity logs.
- `tests/test_activity_log_routes.py`

Tables used by Step 16:

- `activity_logs`
- `projects`
- `tasks`
- `project_members`
- `users`

Current activity behavior:

- Project owners can list activity logs.
- Team project members can list team project activity logs.
- Non-members cannot view team project activity logs.
- Users cannot view another user's personal project activity logs.
- Activity logs are ordered newest first.
- Activity logs support event-type filtering.
- Activity logs support `limit` and `offset` pagination.
- Invalid activity event type, limit, or offset returns `422`.
- Unauthenticated access returns `401`.
- Activity logs preserve snapshots for deleted or changed objects where needed.

## Step 17 — Progress Tracking and Productivity Insights Completed

Step 17 adds backend progress tracking and productivity insights.

Step 17 endpoint:

- `GET /projects/{project_id}/progress`

Step 17 files:

- `app/models/user_progress.py`
- `app/schemas/progress_schema.py`
- `app/services/progress_service.py`
- `app/routers/progress_routes.py`
- Updated `app/main.py`.
- Updated `app/models/user.py`.
- Updated `app/models/project.py`.
- Updated `app/models/__init__.py`.
- `tests/test_09_progress_api.py`

Tables used by Step 17:

- `projects`
- `tasks`
- `project_members`
- `users`
- `user_progress`

Current progress behavior:

- Personal project owner can view project progress.
- Team project members can view team project progress.
- Cross-user personal project access returns `404 Project not found`.
- Missing or invalid bearer token returns `401 Unauthorized`.
- Backend calculates total tasks, completed tasks, pending tasks, overdue tasks, task status counts, hours summary, current user progress, member progress, productivity status, and recommendations.
- Backend upserts rows into `user_progress`.

## Step 18 — Project Member Role Update Completed

Step 18 adds a project-member role update endpoint for team projects.

Step 18 endpoint:

- `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}`

Step 18 files:

- Updated `app/schemas/project_schema.py` with `ProjectAssignableRole` and `ProjectMemberUpdate`.
- Updated `app/services/project_service.py` with `update_project_member_role()`.
- Updated `app/routers/team_project_routes.py` with the project-member role update route.
- Added `tests/test_10_project_member_roles_api.py`.

Tables used by Step 18:

- `projects`
- `project_members`
- `team_members`
- `users`

Current project role behavior:

- Only the project owner can update project member roles.
- Allowed target roles are `manager` and `member`.
- `owner` cannot be assigned through this endpoint.
- The existing project owner role cannot be changed through this endpoint.
- Project managers cannot update project member roles.
- Missing or invalid bearer token returns `401 Unauthorized`.
- Unauthorized role update returns `403 Forbidden`.
- Missing project returns `404 Project not found`.
- Missing project member returns `404 Project member not found`.

Testing:

- Step 18 added 4 pytest route tests.
- User confirmed full regression result after Step 18: `56 passed`.

No SQL migration is required for Step 18 because `project_members.role` already allows `owner`, `manager`, and `member`.

## Role Management Decision

There are two separate membership systems:

- `team_members.role`: `owner`, `admin`, `member`.
- `project_members.role`: `owner`, `manager`, `member`.

Team role endpoint:

- `PATCH /teams/{team_id}/members/{user_id}` updates `team_members.role`.
- Only the team owner should be allowed to update team member roles.
- Team member role update should only allow `admin` and `member`.
- Do not allow assigning `owner` through normal role update.
- Ownership transfer should be a separate future feature if needed.

Project role endpoint:

- `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}` updates `project_members.role`.
- Only the project owner can update project member roles.
- Project member role update allows changing between `manager` and `member`.
- It does not allow assigning `owner` through normal role update.
- The current project owner role cannot be changed through this endpoint.

Important behavior:

- If user 2 is changed to team `admin`, `GET /teams/{team_id}/members` should show admin.
- `GET /teams/{team_id}/projects/{project_id}/members` can still show project `member` for existing projects because that reads `project_members.role`.
- This is expected, not a bug.

## Current Main Tables

- `users`
- `teams`
- `team_members`
- `projects`
- `project_members`
- `tasks`
- `attachments`
- `comments`
- `comment_mentions`
- `notifications`
- `invitations`
- `deadline_reminders`
- `activity_logs`
- `ai_plans`
- `risk_analysis`
- `user_progress`
- `chat_messages`
- `admin_logs`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

Planned/polish tables:

- `device_tokens` for Firebase Cloud Messaging tokens.
- `notification_preferences`.
- Optional report export history table only if the system later needs saved/download history. Step 15 does not need it.

## Roadmap From Here

Immediate cleanup:

- Clean duplicate import blocks in `app/routers/team_project_routes.py` after Step 18.
- Keep expanding pytest coverage for future features and edge cases.

Next feature step candidates:

- AI project planning.
- Smart scheduling.
- Risk analysis and delay prediction.
- AI chat assistant.
- Admin dashboard APIs.

Later steps:

- CORS/frontend/mobile integration.
- Firebase FCM for push notifications.
- Firebase Storage for attachments.
- Tests/security cleanup/Alembic.
- Docker and deployment polish.

## User Preference

- Do not provide long PowerShell test scripts by default.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them with the same terminal pattern used for Step 14 and later.
- If the user asks to create tests only, do not create the whole feature step.
- When updating the repo, avoid adding new feature files unless the user explicitly asks for implementation.
