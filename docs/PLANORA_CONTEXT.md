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

## Current Verified Status — 2026-05-15

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

Important current notes:

- Google-created accounts cannot use Swagger password authorization unless they set a Planora password through forgot/reset password.
- Google-created users normally authenticate through `POST /auth/google` and receive a Planora JWT.
- `notifications.type` must allow: `task`, `project`, `team`, `comment`, `mention`, `invite`, `deadline`, `ai`, `risk`, `system`.
- If invitation, mention, or deadline notifications fail when inserting notification types, fix the live PostgreSQL notification check constraint.
- Team roles and project roles are separate.
- Updating `team_members.role` does not update `project_members.role`.
- A team `admin` is not automatically a project `manager`.

## Regression Testing Status — 2026-05-15

A pytest regression suite exists in the `tests/` folder and should be used after every backend feature step.

Latest user-confirmed local result after Step 14:

- 29 tests collected.
- 29 tests passed.
- Command used: `python -m pytest -x -v`.

Previous verified result before Step 14:

- 25 tests collected.
- 25 tests passed.
- Runtime around 3.29 seconds on the user's local machine.

Current test coverage includes:

- Authentication registration, weak-password rejection, verified-login behavior, `/auth/me`, duplicate email rejection, and missing-token protection.
- Personal project CRUD and cross-user access protection.
- Personal task CRUD and completed-task timestamp behavior.
- Team creation, owner membership, adding members, and updating team member roles.
- Team project creation and team task update flow.
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
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions for permissions, success cases, and duplicate/edge cases.
- Keep using `python -m pytest -x -v` as the first full regression check.

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
- `app/main.py` includes `invitation_router`

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

Recommended SQL for existing databases:

```sql
CREATE TABLE IF NOT EXISTS comment_mentions (
    mention_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    comment_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    task_id BIGINT NOT NULL,
    mentioned_user_id BIGINT NOT NULL,
    mentioned_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comment_mentions_comment
        FOREIGN KEY (comment_id)
        REFERENCES comments(comment_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_project
        FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_task
        FOREIGN KEY (task_id)
        REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_mentioned_user
        FOREIGN KEY (mentioned_user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_mentioned_by
        FOREIGN KEY (mentioned_by)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_mentions_comment_user
        UNIQUE (comment_id, mentioned_user_id)
);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_comment
ON comment_mentions(comment_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_project
ON comment_mentions(project_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_task
ON comment_mentions(task_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_mentioned_user
ON comment_mentions(mentioned_user_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_mentioned_by
ON comment_mentions(mentioned_by);
```

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
- Updated `app/main.py` to include `deadline_reminder_router`
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

Recommended SQL for existing databases:

```sql
CREATE TABLE IF NOT EXISTS deadline_reminders (
    reminder_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reminder_type VARCHAR(30) NOT NULL,
    due_date_snapshot TIMESTAMPTZ NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_deadline_reminders_task
        FOREIGN KEY (task_id)
        REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_deadline_reminders_project
        FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_deadline_reminders_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_deadline_reminders_type
        CHECK (reminder_type IN ('due_soon', 'overdue')),
    CONSTRAINT uq_deadline_reminders_task_user_type_due_date
        UNIQUE (task_id, user_id, reminder_type, due_date_snapshot)
);

CREATE INDEX IF NOT EXISTS idx_deadline_reminders_task
ON deadline_reminders(task_id);

CREATE INDEX IF NOT EXISTS idx_deadline_reminders_project
ON deadline_reminders(project_id);

CREATE INDEX IF NOT EXISTS idx_deadline_reminders_user
ON deadline_reminders(user_id);

CREATE INDEX IF NOT EXISTS idx_deadline_reminders_type
ON deadline_reminders(reminder_type);

CREATE INDEX IF NOT EXISTS idx_deadline_reminders_generated_at
ON deadline_reminders(generated_at);
```

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

Project role endpoint still needed:

- Add `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}`.
- This should update `project_members.role`.
- It should allow changing between `manager` and `member`.
- It should not allow assigning `owner` through normal role update.

Important behavior:

- If user 2 is changed to team `admin`, `GET /teams/{team_id}/members` should show admin.
- `GET /teams/{team_id}/projects/{project_id}/members` can still show project `member` because that reads `project_members.role`.
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
- `ai_plans`
- `risk_analysis`
- `user_progress`
- `chat_messages`
- `admin_logs`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

Planned/polish tables:

- `activity_logs`
- `device_tokens` for Firebase Cloud Messaging tokens
- `notification_preferences`
- Optional report export history table

## Roadmap From Here

Immediate cleanup:

- Add project-member role update endpoint.
- Keep expanding pytest coverage for future features and edge cases.
- Consider adding tests for project-member role update permissions after that endpoint is implemented.

Next feature step:

- Progress tracking and productivity insights.

Later steps:

- Activity timeline.
- AI project planning and smart scheduling.
- Risk analysis.
- AI chat assistant.
- Export project report.
- Admin dashboard APIs.
- CORS/frontend/mobile integration.
- Firebase FCM for push notifications.
- Firebase Storage for attachments.
- Tests/security cleanup/Alembic.
- Docker and deployment polish.

## User Preference

- Do not provide long PowerShell test scripts by default.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them with the same terminal pattern used for Step 14.
