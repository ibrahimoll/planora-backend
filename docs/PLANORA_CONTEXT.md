# Planora Backend Context

Last updated: 2026-05-17

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, and local rule-based AI with optional Gemini provider configuration.

## Current Verified Status

Latest confirmed clean full regression result:

- `105 passed`
- Confirmed after Step 25 Productivity Insights Center.
- Previous confirmed result was `101 passed` after Admin Control Center expansion from Step 23.2 through Step 23.6.
- Test database requirement: `TEST_DATABASE_URL` must point to `planora_test_db`, not the normal development database.

Latest in-progress regression attempt after Codex cleanup:

- Command used: `python -m pytest -x -v`.
- Pytest collected `113 items`.
- Result before stopping with `-x`: `21 passed`, `1 failed`.
- Failure is not a real API bug; it is a stale test assertion in `tests/test_07_deadline_reminders_api.py`.
- The backend now correctly returns `403 Forbidden` with detail `Admin access required.` from the shared `get_current_admin_user` dependency.
- The old test still expected `Only admins can run deadline reminder scans`.
- Immediate fix: update the expected detail in `test_non_admin_cannot_run_deadline_scan` to `Admin access required.`, then rerun `python -m pytest -x -v` and finally `python -m pytest -v`.

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
23. Admin Control Center foundation — admin user management.
23.1. Admin Project Oversight.
23.2. Admin Task Oversight.
23.3. Admin Risk Center.
23.4. Admin Reports Center.
23.5. Admin Logs Filters and Audit Improvements.
23.6. Admin User Search/Filters and User Activity View.
24. AI Chat Assistant MVP.
25. Productivity Insights Center.

Latest completed feature groups:

- Step 24 — AI Chat Assistant MVP.
- Step 25 — Productivity Insights Center.
- Codex backend security/cleanup pass after AI chat and productivity insights.

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
- Optional report export history table only if saved/download history is needed.

## Authentication and Admin Rules

Normal login endpoint:

- `POST /auth/login`

There is no separate admin login endpoint. Admins login normally, then admin routes check `users.role`.

Rules:

- Public registration always creates normal users with `role = 'user'`.
- Public registration must never accept `role = 'admin'`.
- First admin should be promoted manually in PostgreSQL.
- After the first admin exists, admins can promote/demote users through `PATCH /admin/users/{user_id}/role`.
- Missing/invalid bearer token returns `401 Unauthorized`.
- Unverified or inactive users are blocked by `get_current_active_verified_user`.
- Normal users accessing admin routes receive `403 Forbidden` with `Admin access required.`.
- Admin-only routes depend on `get_current_admin_user`.
- Route-specific local admin guards should be avoided unless there is a strong reason. Prefer the shared dependency for consistency.

Manual first-admin SQL:

```sql
UPDATE users
SET role = 'admin',
    is_active = true,
    is_email_verified = true
WHERE email = 'your_email@example.com';
```

## Admin Control Center Current Powers

The admin is now an overpowered but audited system commander. Critical admin actions create `admin_logs` rows.

### Step 22 — Admin Dashboard Backend

Endpoints:

- `GET /admin/dashboard/overview`
- `GET /admin/users`
- `GET /admin/dashboard/recent-activity`
- `GET /admin/logs`

Admin can view system statistics, users, recent activity, and admin logs.

### Step 23 — Admin User Management

Endpoints:

- `GET /admin/users/{user_id}`
- `GET /admin/users/{user_id}/activity`
- `PATCH /admin/users/{user_id}/deactivate`
- `PATCH /admin/users/{user_id}/activate`
- `PATCH /admin/users/{user_id}/role`

Admin can view user details/activity, activate/deactivate users, and promote/demote users. Protections: admin cannot deactivate self, remove own admin role, or remove/deactivate the last active verified admin.

### Step 23.1 — Admin Project Oversight

Endpoints:

- `GET /admin/projects`
- `GET /admin/projects/{project_id}`
- `PATCH /admin/projects/{project_id}/status`

Admin can list/filter all projects, view project details, task counts, overdue/blocked counts, completion percentage, members count, latest risk, and moderate projects by status changes.

### Step 23.2 — Admin Task Oversight

Endpoints:

- `GET /admin/tasks`
- `GET /admin/tasks/{task_id}`
- `PATCH /admin/tasks/{task_id}/status`
- `PATCH /admin/tasks/{task_id}/assignment`

Admin can list/filter all tasks, view task details, change task status, assign tasks, and unassign tasks. Supported task filters include status, priority, project, assignee, creator, overdue, unassigned, and search text.

### Step 23.3 — Admin Risk Center

Endpoints:

- `GET /admin/risk/summary`
- `GET /admin/risk/high-risk-projects`

Admin can view system-level risk summary and list high-risk projects using latest risk records.

### Step 23.4 — Admin Reports Center

Endpoints:

- `GET /admin/reports/system-summary`
- `GET /admin/reports/projects-summary`
- `GET /admin/reports/users-summary`

Admin can generate JSON reports for system, projects, and users.

### Step 23.5 — Admin Logs Filters

Updated endpoint:

- `GET /admin/logs`

Supported filters:

- `admin_id`
- `target_user_id`
- `action`
- `created_from`
- `created_to`
- `limit`
- `offset`

### Step 23.6 — Admin User Search/Filters

Updated endpoint:

- `GET /admin/users`

Supported filters:

- `role`
- `is_active`
- `is_email_verified`
- `search`
- `limit`
- `offset`

## Admin Expansion Files

Task oversight:

- `app/schemas/admin_task_oversight_schema.py`
- `app/services/admin_task_oversight_service.py`
- `app/routers/admin_task_oversight_routes.py`

Risk/reports:

- `app/schemas/admin_risk_report_schema.py`
- `app/services/admin_risk_report_service.py`
- `app/routers/admin_risk_report_routes.py`

Updated files:

- `app/main.py`
- `app/services/admin_dashboard_service.py`
- `app/routers/admin_dashboard_routes.py`
- `app/services/admin_user_management_service.py`
- `app/routers/admin_user_management_routes.py`

Tests:

- `tests/test_15_admin_control_center_expansion_api.py`

## AI / Intelligence Features

AI Project Planning MVP:

- Saves generated plans in `ai_plans`.
- Can optionally create tasks from generated plans.
- Uses local deterministic/rule-based logic named `local_rule_based_v1`.

Risk Analysis / Delay Prediction MVP:

- Saves generated risk snapshots in `risk_analysis`.
- Calculates risk using project deadline, task completion, overdue tasks, blocked tasks, and remaining estimated hours.
- Saved high-risk analyses create in-app `risk` notifications.
- Uses local deterministic/rule-based logic.

Smart Scheduling MVP:

- Saves generated schedule snapshots in `smart_schedules`.
- Can preview schedules without modifying tasks.
- Can optionally apply generated schedules by updating incomplete task due dates.
- Uses local deterministic balanced scheduling strategy.

AI provider status after Codex cleanup:

- Default AI provider is `local`.
- `.env.example` documents `AI_PROVIDER=local`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`, and `GEMINI_TIMEOUT_SECONDS=15`.
- Gemini provider code is optional and falls back to local AI if provider/API configuration fails.
- Raw Gemini response/body logging and debug `print()` output were removed from `app/services/ai_provider_service.py`.
- Do not log full prompt bodies, raw model responses, tokens, API keys, passwords, JWTs, or private user data.

Future AI integration rule:

- Replace only generator/analyzer/scheduler/chat-provider logic inside service files while keeping the same API contracts.

## Step 24 — AI Chat Assistant MVP

Endpoints:

- `POST /projects/{project_id}/chat`
- `GET /projects/{project_id}/chat`
- `POST /teams/{team_id}/projects/{project_id}/chat`
- `GET /teams/{team_id}/projects/{project_id}/chat`

Files:

- `app/routers/ai_chat_routes.py`
- `app/services/ai_chat_service.py`
- `app/services/ai_provider_service.py`
- `app/schemas/ai_chat_schema.py`
- `tests/test_17_ai_chat_assistant_api.py`

Current behavior:

- Active verified users can chat with AI for personal projects they own.
- Team project members can chat with AI for team projects they belong to.
- Non-members are blocked from team project chat.
- The assistant builds context from project details, tasks, latest risk analysis, and recent chat history.
- User messages are saved in `chat_messages` with `sender_type = 'user'` and `sender_id` set to the current user.
- AI messages are saved in `chat_messages` with `sender_type = 'ai'` and `sender_id = NULL`.
- Tests were corrected to assert `sender_id`, not stale `user_id`.

## Step 25 — Productivity Insights Center

Endpoint:

- `GET /insights/me`

Files added/updated:

- Added `app/schemas/productivity_insight_schema.py`.
- Added `app/services/productivity_insight_service.py`.
- Added `app/routers/productivity_insight_routes.py`.
- Updated `app/main.py` to include `productivity_insight_router`.
- Added `tests/test_16_productivity_insights_api.py`.

Tables used:

- `users`
- `projects`
- `project_members`
- `tasks`
- `user_progress` indirectly remains part of the progress system, but Step 25 does not need a new table or migration.

Current behavior:

- Active verified users can request their own productivity insights.
- Missing/invalid token returns `401 Unauthorized`.
- Personal projects are included only when owned by the current user.
- Team projects are included when the current user is a project member.
- Other users' personal projects are excluded.
- Response includes project totals, active/completed project counts, total visible task count, assigned task counts, completed assigned tasks, overdue assigned tasks, blocked assigned tasks, completion percentage, workload summary, per-project health, and rule-based recommendations.
- Workload is marked overloaded when assigned incomplete tasks are high or remaining estimated hours are high.
- Project health can be `excellent`, `good`, `needs_attention`, or `at_risk`.

Testing:

- Step 25 added 4 API tests.
- User confirmed Step 25 feature tests and full regression result: `105 passed`.

## Codex Backend Security/Cleanup Pass — 2026-05-17

Codex latest pushed cleanup changed these files:

- `.env.example`
- `app/models/password_reset_code.py`
- `app/routers/deadline_reminder_routes.py`
- `app/services/ai_provider_service.py`
- `app/services/profile_service.py`
- `tests/test_17_ai_chat_assistant_api.py`

Confirmed cleanup results:

- No critical issues found in the reviewed backend code.
- `.env` is ignored and should not be tracked.
- No obvious committed API/private-key patterns were found during the review.
- Gemini raw response/body logging and debug prints were removed.
- Deadline reminder admin scan now uses shared `get_current_admin_user`.
- Duplicate imports were cleaned in profile service.
- AI chat tests were updated to expect `sender_id`, not stale `user_id`.
- `.env.example` now documents local AI and Gemini placeholders.
- `password_reset_codes` SQLAlchemy model now includes `chk_password_reset_codes_expiry` with `expires_at > created_at`.

Important remaining items after Codex cleanup:

- Run the full DB-backed suite after fixing the stale deadline reminder test assertion.
- Add the live PostgreSQL migration for `chk_password_reset_codes_expiry`; model changes do not update existing tables automatically.
- CORS is still not configured in `app/main.py`; add explicit allowlist CORS when frontend/mobile browser integration starts.
- If `database/database_schema.sql` exists locally, align it with SQLAlchemy models or replace manual schema drift with migrations/Alembic.
- Ruff is not installed yet; lint cleanup remains manual unless the project adds Ruff later.

Live DB migration still required:

```sql
ALTER TABLE password_reset_codes
DROP CONSTRAINT IF EXISTS chk_password_reset_codes_expiry;

ALTER TABLE password_reset_codes
ADD CONSTRAINT chk_password_reset_codes_expiry
CHECK (expires_at > created_at);
```

Verification SQL:

```sql
SELECT conname
FROM pg_constraint
WHERE conname = 'chk_password_reset_codes_expiry';
```

## Role Management Decision

There are separate role systems:

- Global user role: `users.role`: `user`, `admin`.
- Team membership role: `team_members.role`: `owner`, `admin`, `member`.
- Project membership role: `project_members.role`: `owner`, `manager`, `member`.

Important behavior:

- Changing a user to global `admin` gives access to admin dashboard routes.
- It does not automatically change team or project membership roles.
- Team role and project role updates remain separate features.

## Regression Testing

Standard local pytest command pattern:

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
```

Useful local commands:

```powershell
python -m pytest tests/test_16_productivity_insights_api.py -v
python -m pytest tests/test_17_ai_chat_assistant_api.py -v
python -m pytest --collect-only -q
python -m pytest --cov=app --cov-report=term-missing
python -m compileall app tests
python -m pip check
```

Current known test fix needed:

```python
assert response.json()["detail"] == "Admin access required."
```

This should replace the stale expected message in `tests/test_07_deadline_reminders_api.py::test_non_admin_cannot_run_deadline_scan`.

Future testing rule:

- Every backend feature step should include pytest tests before the step is considered done.
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions.
- Keep using `python -m pytest -x -v` as the first full regression check.
- After `-x` passes, run `python -m pytest -v` for the final full result.

## Roadmap From Here

Immediate next actions:

1. Fix stale deadline reminder test expected detail.
2. Rerun DB-backed full pytest suite until clean.
3. Add live PostgreSQL migration for `chk_password_reset_codes_expiry`.
4. Commit and push the test/memo updates.

Next feature/polish candidates:

- Real AI API integration hardening.
- Productivity insights expansion.
- CORS/frontend/mobile integration.
- Firebase FCM for push notifications.
- Firebase Storage for attachments.
- Tests/security cleanup/Alembic.
- Docker and deployment polish after the core system is stable.

## User Preference

- When the user says `done` or gives a test result after a backend step, update `docs/PLANORA_CONTEXT.md`.
- Do not provide long PowerShell test scripts by default.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them.
- Keep Docker as final polish after core system features are stable.
- Keep this file as the main Planora project memory inside VS Code/Codex so the chat memory does not become too large.
