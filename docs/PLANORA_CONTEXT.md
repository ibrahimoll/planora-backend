# Planora Backend Context

Last updated: 2026-05-16

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

The backend currently uses FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, Google social login, SMTP email for verification/reset flows, and local file storage for development.

## Current Verified Status

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
18.1. Cleanup duplicate imports in team project routes.
19. AI project planning MVP.
20. Risk analysis / delay prediction MVP.
20.1. Risk notifications for high-risk projects.
21. Smart scheduling MVP.
22. Admin dashboard backend.

Latest confirmed full regression result:

- `82 passed`
- Confirmed after Step 22 Admin Dashboard Backend.
- Test database requirement: `TEST_DATABASE_URL` must point to `planora_test_db`, not the normal development database.

Latest completed feature step:

- Step 22 — Admin Dashboard Backend.
- Added 4 new admin dashboard tests.
- Previous result after Step 21 was `78 passed`; Step 22 increased the suite to `82 passed`.

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
- `smart_schedules`
- `user_progress`
- `chat_messages`
- `admin_logs`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

Planned/polish tables:

- `device_tokens` for Firebase Cloud Messaging tokens.
- `notification_preferences`.
- Optional report export history table only if the system later needs saved/download history.

## Authentication and Admin Access Rules

Normal login endpoint:

- `POST /auth/login`

There is no separate admin login endpoint. Admins login with the same normal login flow, then protected admin routes check `users.role`.

Admin access rule:

- Public registration must always create normal users with `role = 'user'`.
- Never allow public registration to accept `role = 'admin'`.
- A user becomes admin only when `users.role = 'admin'` in PostgreSQL or when a future existing-admin endpoint promotes them.
- First admin should be promoted manually in PostgreSQL.
- Future admin promotion should be implemented in Step 23 through an admin-only endpoint.

Manual first-admin SQL:

```sql
UPDATE users
SET role = 'admin',
    is_active = true,
    is_email_verified = true
WHERE email = 'your_email@example.com';
```

Protected route rules:

- Missing or invalid bearer token returns `401 Unauthorized`.
- Unverified or inactive users are blocked by `get_current_active_verified_user`.
- Authenticated normal users trying to access admin routes receive `403 Forbidden` with `Admin access required.`.
- Admin-only routes should depend on `get_current_admin_user`.

Google login notes:

- Google-created users authenticate through `POST /auth/google` and receive a Planora JWT.
- Google-created accounts cannot use Swagger password authorization unless they set a Planora password through forgot/reset password.
- `/auth/me` requires a Planora JWT, not a raw Google token.

## Current AI / Intelligence Features

AI Project Planning MVP:

- Saves generated plans in `ai_plans`.
- Can optionally create tasks from generated plans.
- Uses local deterministic/rule-based logic named `local_rule_based_v1`.
- Real OpenAI/Gemini integration is not connected yet.

Risk Analysis / Delay Prediction MVP:

- Saves generated risk snapshots in `risk_analysis`.
- Calculates risk using project deadline, task completion, overdue tasks, blocked tasks, and remaining estimated hours.
- When a saved risk analysis is `high`, the backend creates in-app `risk` notifications for affected project users.
- Uses local deterministic/rule-based logic.

Smart Scheduling MVP:

- Saves generated schedule snapshots in `smart_schedules`.
- Can preview schedules without modifying tasks.
- Can optionally apply generated schedules by updating incomplete task due dates.
- Uses local deterministic balanced scheduling strategy.

Future AI integration rule:

- Replace only generator/analyzer/scheduler logic inside service files while keeping the same API contracts.

## Firebase Decision

- Firebase Cloud Messaging will be used later for real mobile push notifications.
- Firebase Storage will be used later for attachments/files.
- For now, notifications are stored as in-app rows in the `notifications` table.
- For now, attachments are stored locally during backend development.

## Step 12 — Invitation System Completed

Step 12 uses the existing `invitations` table. Do not create a separate `team_invitations` table.

Endpoints:

- `POST /teams/{team_id}/invitations`
- `GET /invitations/me`
- `POST /invitations/{invitation_id}/accept`
- `POST /invitations/{invitation_id}/reject`

Current behavior:

- Team owner/admin invites by Planora username.
- Backend resolves `users.username` to `invited_user_id`.
- Backend creates a pending row in `invitations`.
- Backend creates an in-app notification with `type = invite`.
- Invited user can accept or reject.
- Accepting adds the user to `team_members`.
- Accepting also adds the user to existing team projects as project `member`, unless already present.
- Prevent duplicate pending invitations for the same team and invited user.

## Step 13 — Mentions in Comments Completed

Step 13 adds `@username` mentions inside task comments.

Current behavior:

- Backend parses mentioned usernames from `comment_text`.
- Duplicate usernames inside one comment are ignored.
- Backend checks that the mentioned username exists and belongs to the same project.
- Mention rows are saved in `comment_mentions`.
- Mention notifications use `notifications.type = 'mention'`.
- The author should not receive a notification for mentioning themselves.
- Updating a comment replaces old mention rows based on the new text.

## Step 14 — Deadline Reminders Completed

Endpoints:

- `POST /deadline-reminders/run`
- `GET /deadline-reminders/me`

Current behavior:

- Admins can manually run a deadline scan.
- Normal users cannot run the scan.
- Incomplete assigned tasks near due date create `due_soon` reminders.
- Incomplete assigned overdue tasks create `overdue` reminders when `include_overdue = true`.
- Completed tasks are ignored.
- Tasks without assignees or due dates are ignored.
- Duplicate reminders are prevented by the `deadline_reminders` table unique rule.
- Reminder creation creates an in-app notification with `type = deadline`.

## Step 15 — Export Project Report Completed

Endpoint:

- `GET /reports/projects/{project_id}`

Current behavior:

- Personal project owner can export the report.
- Team project members can export the report.
- Cross-user personal project access returns `404 Project not found`.
- Missing token returns `401 Unauthorized`.
- Returns JSON only for now; frontend/mobile can later convert it to PDF or render it as a report screen.

Tables used:

- `projects`
- `tasks`
- `project_members`
- `users`
- `comments`
- `attachments`
- `deadline_reminders`

## Step 16 — Activity Timeline / Activity Logs Completed

Endpoint:

- `GET /projects/{project_id}/activity`

Current behavior:

- Personal project owners can list activity logs.
- Team project members can list team project activity logs.
- Non-members cannot view team project activity logs.
- Users cannot view another user's personal project activity logs.
- Activity logs are ordered newest first.
- Supports event-type filtering and `limit`/`offset` pagination.
- Step 19 added `ai_plan_generated` as an activity event type.

## Step 17 — Progress Tracking and Productivity Insights Completed

Endpoint:

- `GET /projects/{project_id}/progress`

Current behavior:

- Personal project owner can view project progress.
- Team project members can view team project progress.
- Cross-user personal project access returns `404 Project not found`.
- Backend calculates task counts, overdue tasks, hours summary, current user progress, member progress, productivity status, and recommendations.
- Backend upserts rows into `user_progress`.

## Step 18 — Project Member Role Update Completed

Endpoint:

- `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}`

Current behavior:

- Only project owner can update project member roles.
- Allowed target roles are `manager` and `member`.
- `owner` cannot be assigned through this endpoint.
- The current project owner role cannot be changed through this endpoint.
- Project managers cannot update project member roles.

## Step 18.1 — Import Cleanup Completed

- Cleaned duplicate import blocks in `app/routers/team_project_routes.py`.
- No endpoint behavior changed.

## Step 19 — AI Project Planning MVP Completed

Endpoints:

- `POST /projects/{project_id}/ai-plans`
- `GET /projects/{project_id}/ai-plans`
- `POST /teams/{team_id}/projects/{project_id}/ai-plans`
- `GET /teams/{team_id}/projects/{project_id}/ai-plans`

Current behavior:

- Personal project owners can generate AI plans.
- Personal project AI plans can optionally create tasks.
- Personal project generated tasks are assigned to the current user.
- Team project owners/managers can generate AI plans.
- Normal team project members cannot generate AI plans.
- Team project generated tasks are created unassigned.
- Generated plans are saved in `ai_plans.generated_plan` as JSONB.
- Activity logs support `ai_plan_generated`.

Testing:

- Step 19 full regression result: `63 passed`.

## Step 20 — Risk Analysis / Delay Prediction MVP Completed

Endpoints:

- `GET /projects/{project_id}/risk-analysis/preview`
- `POST /projects/{project_id}/risk-analysis`
- `GET /projects/{project_id}/risk-analysis`

Current behavior:

- Personal project owners can preview and generate risk analysis.
- Team project members can access risk analysis for team projects they belong to.
- Users cannot access another user's personal project risk analysis.
- Preview calculates risk but does not save a row.
- Generate calculates risk and saves a row in `risk_analysis`.
- List returns saved risk analyses ordered newest first.
- Risk level can be `low`, `medium`, or `high`.
- Predicted delay days is never negative.

## Step 20.1 — Risk Notifications Completed

Current behavior:

- Saved high-risk analyses create in-app notifications with `type = 'risk'`.
- Personal project high-risk notifications go to the project owner.
- Team project high-risk notifications go to project members.
- Low and medium risk analyses do not create risk notifications.

Testing:

- Step 20.1 feature result: `9 passed`.

## Step 21 — Smart Scheduling MVP Completed

Endpoints:

- `POST /projects/{project_id}/smart-schedules/preview`
- `POST /projects/{project_id}/smart-schedules`
- `GET /projects/{project_id}/smart-schedules`
- `POST /teams/{team_id}/projects/{project_id}/smart-schedules/preview`
- `POST /teams/{team_id}/projects/{project_id}/smart-schedules`
- `GET /teams/{team_id}/projects/{project_id}/smart-schedules`

Files:

- `app/models/smart_schedule.py`
- `app/schemas/smart_schedule_schema.py`
- `app/services/smart_schedule_service.py`
- `app/routers/smart_schedule_routes.py`
- `tests/test_12_smart_schedules_api.py`

Tables used:

- `smart_schedules`
- `projects`
- `tasks`
- `project_members`
- `users`

Current behavior:

- Personal project owners can preview, generate, save, and optionally apply smart schedules.
- Team project members can preview and list smart schedules.
- Team project owners/managers can generate smart schedules.
- Normal team project members cannot generate/apply saved smart schedules.
- Completed tasks are ignored by the scheduler.
- Incomplete tasks are sorted by priority: high, medium, then low.
- Scheduler uses daily capacity hours and currently supports `balanced` strategy.
- Schedule payloads are saved in `smart_schedules.schedule_data` as JSONB.

Testing:

- Step 21 feature result: `6 passed`.
- Full regression after Step 21: `78 passed`.

## Step 22 — Admin Dashboard Backend Completed

Step 22 added backend APIs for the web admin dashboard.

Endpoints:

- `GET /admin/dashboard/overview`
- `GET /admin/users`
- `GET /admin/dashboard/recent-activity`
- `GET /admin/logs`

Files added/updated:

- Added `app/models/admin_log.py`.
- Added `app/schemas/admin_dashboard_schema.py`.
- Added `app/services/admin_dashboard_service.py`.
- Added `app/routers/admin_dashboard_routes.py`.
- Updated `app/models/user.py` with admin-log relationships.
- Updated `app/models/__init__.py` to import `AdminLog`.
- Updated `app/dependencies/auth.py` with `get_current_admin_user`.
- Updated `app/main.py` to include `admin_dashboard_router`.
- Added `tests/test_admin_dashboard_routes.py`.

Tables used:

- `users`
- `projects`
- `tasks`
- `teams`
- `risk_analysis`
- `notifications`
- `activity_logs`
- `admin_logs`

Current behavior:

- Admin dashboard overview returns user, project, task, team, risk, and notification statistics.
- Admin users endpoint returns paginated users.
- Recent activity endpoint returns newest activity logs.
- Admin logs endpoint returns newest admin logs.
- Admin routes require an active, verified user with `users.role = 'admin'`.
- Normal users receive `403 Forbidden` with `Admin access required.`.
- Missing or invalid token returns `401 Unauthorized`.
- Admins login through the normal `/auth/login` route; there is no separate admin login.

Live database SQL for `admin_logs` if needed:

```sql
CREATE TABLE IF NOT EXISTS admin_logs (
    log_id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    target_user_id BIGINT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id
ON admin_logs(admin_id);

CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user_id
ON admin_logs(target_user_id);

CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at
ON admin_logs(created_at);
```

Testing:

- Step 22 added 4 admin dashboard API tests.
- Test coverage includes normal-user admin denial, admin dashboard overview, admin users listing, and recent activity/admin logs routes.
- User confirmed full regression result after Step 22: `82 passed`.

Commit message used/recommended:

```bash
git add .
git commit -m "Add admin dashboard backend endpoints"
git push
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

Project role endpoint:

- `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}` updates `project_members.role`.
- Only the project owner can update project member roles.
- Project member role update allows changing between `manager` and `member`.
- It does not allow assigning `owner` through normal role update.
- The current project owner role cannot be changed through this endpoint.

Important behavior:

- If a user is changed to team `admin`, `GET /teams/{team_id}/members` should show admin.
- `GET /teams/{team_id}/projects/{project_id}/members` can still show project `member` for existing projects because that reads `project_members.role`.
- This is expected, not a bug.

## Regression Testing Status

A pytest regression suite exists in the `tests/` folder and should be used after every backend feature step.

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
- `tests/test_11_ai_plans_api.py`
- `tests/test_12_smart_schedules_api.py`
- `tests/test_admin_dashboard_routes.py`
- `tests/test_risk_analysis.py`
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
- Only test files should be created using terminal commands when the user specifically says: "only test files are created using a command".

## Roadmap From Here

Recommended next step:

- Step 23 — Admin User Management.

Step 23 should include:

- Admin deactivate user.
- Admin activate user.
- Admin change user role.
- Admin view user details.
- Admin log creation when admin performs actions.

Later feature step candidates:

- Real AI API integration for AI project planning, risk analysis, and smart scheduling.
- AI chat assistant.
- Productivity insights expansion.
- CORS/frontend/mobile integration.
- Firebase FCM for push notifications.
- Firebase Storage for attachments.
- Tests/security cleanup/Alembic.
- Docker and deployment polish.

## User Preference

- When the user says `done` after a backend step/test, update `docs/PLANORA_CONTEXT.md`.
- Do not provide long PowerShell test scripts by default.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them with the same terminal pattern used for Step 14 and later.
- If the user asks to create tests only, do not create the whole feature step.
- When updating the repo, avoid adding new feature files unless the user explicitly asks for implementation.
- Keep Docker as final polish after core system features are stable.