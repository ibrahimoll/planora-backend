# Planora Backend Context

Last updated: 2026-05-17

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, local rule-based AI with optional Gemini provider configuration, explicit CORS/frontend-mobile integration, Firebase Cloud Messaging real push sending, and manual Firebase web-push testing helpers.

## Current Verified Status

Latest confirmed clean full regression result:

- `129 passed`
- Confirmed after Step 28 Firebase Cloud Messaging real push sending.
- Step 28 isolated test result: `5 passed` for `tests/test_20_firebase_push_service.py`.
- Step 28 manual Swagger result confirmed Firebase accepted one real push: `status = sent`, `sent_count = 1`, `failed_count = 0`.
- Previous confirmed clean full regression result was `124 passed` after Step 27 CORS / Frontend-Mobile Integration.
- Previous confirmed clean result was `119 passed` after Step 26 Push Notification Foundation.
- Previous confirmed clean result before that was `105 passed` after Step 25 Productivity Insights Center.
- Previous confirmed result before that was `101 passed` after Admin Control Center expansion from Step 23.2 through Step 23.6.
- Test database requirement: `TEST_DATABASE_URL` must point to `planora_test_db`, not the normal development database.

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
26. Push Notification Foundation.
27. CORS / Frontend-Mobile Integration.
28. Firebase Cloud Messaging real push sending.
29. Alembic Migration Setup.

Latest completed feature groups:

- Step 24 — AI Chat Assistant MVP.
- Step 25 — Productivity Insights Center.
- Step 26 — Push Notification Foundation.
- Step 27 — CORS / Frontend-Mobile Integration.
- Step 28 — Firebase Cloud Messaging real push sending.
- Step 29 - Alembic Migration Setup.
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
- `device_tokens`
- `notification_preferences`

Planned/polish tables:

- Optional Firebase push delivery log table only if delivery auditing/history is needed later.
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

## Role Management Decision

There are separate role systems:

- Global user role: `users.role`: `user`, `admin`.
- Team membership role: `team_members.role`: `owner`, `admin`, `member`.
- Project membership role: `project_members.role`: `owner`, `manager`, `member`.

Important behavior:

- Changing a user to global `admin` gives access to admin dashboard routes.
- It does not automatically change team or project membership roles.
- Team role and project role updates remain separate features.

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

Admin expansion files:

- `app/schemas/admin_task_oversight_schema.py`
- `app/services/admin_task_oversight_service.py`
- `app/routers/admin_task_oversight_routes.py`
- `app/schemas/admin_risk_report_schema.py`
- `app/services/admin_risk_report_service.py`
- `app/routers/admin_risk_report_routes.py`

## AI / Intelligence Features

AI Project Planning MVP:

- Saves generated plans in `ai_plans`.
- Can optionally create tasks from generated plans.
- Uses local deterministic/rule-based logic named `local_rule_based_v1`.

Risk Analysis / Delay Prediction MVP:

- Saves generated risk snapshots in `risk_analysis`.
- Calculates risk using project deadline, task completion, overdue tasks, blocked tasks, and remaining estimated hours.
- Saved high-risk analyses create in-app `risk` notifications.
- With Step 28, push sending can also be triggered when a notification is created and Firebase/prefs/tokens allow it.
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

- `app/schemas/productivity_insight_schema.py`
- `app/services/productivity_insight_service.py`
- `app/routers/productivity_insight_routes.py`
- `app/main.py`
- `tests/test_16_productivity_insights_api.py`

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

## Step 26 — Push Notification Foundation

Purpose:

- Prepare Planora for Firebase Cloud Messaging push notifications.
- Store user device tokens from Android, iOS, or web clients.
- Store per-user notification preferences.

Endpoints:

- `POST /push-notifications/device-tokens`
- `GET /push-notifications/device-tokens`
- `PATCH /push-notifications/device-tokens/{device_token_id}/deactivate`
- `GET /push-notifications/preferences`
- `PATCH /push-notifications/preferences`
- `GET /push-notifications/status`

Files added/updated:

- `app/models/device_token.py`
- `app/models/notification_preference.py`
- `app/schemas/push_notification_schema.py`
- `app/services/push_notification_service.py`
- `app/routers/push_notification_routes.py`
- `tests/test_18_push_notifications_api.py`
- `app/main.py`
- `app/models/user.py`
- `app/models/__init__.py`

Tables added:

- `device_tokens`
- `notification_preferences`

Current behavior:

- Active verified users can register or update their own device token.
- Device token platforms are limited to `android`, `ios`, and `web`.
- Users can list their own saved device tokens.
- Users can deactivate their own device tokens.
- Users can get default notification preferences.
- Users can update notification preferences such as `push_enabled`, `deadline_notifications`, and `risk_notifications`.
- Missing/invalid token returns `401 Unauthorized`.

Testing:

- Step 26 added API tests in `tests/test_18_push_notifications_api.py`.
- User confirmed full regression result after Step 26: `119 passed`.

## Step 27 — CORS / Frontend-Mobile Integration

Purpose:

- Allow trusted frontend/admin/mobile-web origins to call the FastAPI backend.
- Prepare Planora for the web admin dashboard and frontend/mobile integration.
- Keep route authentication and authorization rules unchanged.

Files added/updated:

- `app/core/config.py` with `backend_cors_origins`, `cors_allow_credentials`, and `cors_origins`.
- `app/main.py` with FastAPI `CORSMiddleware`.
- `.env.example` with CORS environment variables.
- `tests/test_19_cors_api.py`.

Tables added:

- None.

Current behavior:

- Allowed frontend origins receive CORS headers.
- Disallowed origins do not receive `access-control-allow-origin`.
- Bearer-token Authorization headers are allowed from trusted origins.
- Normal requests without an `Origin` header still work.
- Existing authentication and protected routes remain unchanged.

Testing:

- Step 27 added 5 API tests in `tests/test_19_cors_api.py`.
- User confirmed Step 27 isolated result: `5 passed`.
- User confirmed full regression result after Step 27: `124 passed`.

## Step 28 — Firebase Cloud Messaging Real Push Sending

Purpose:

- Connect the existing push-notification foundation to Firebase Cloud Messaging.
- Send real push notifications to active registered device tokens.
- Respect user notification preferences.
- Deactivate invalid/unregistered FCM tokens after Firebase send errors.
- Keep Firebase credentials out of GitHub.

Endpoints:

- `GET /push-notifications/status`
- `POST /push-notifications/test`
- Existing Step 26 endpoints remain active for device tokens and preferences.

Files added/updated:

- `app/services/firebase_push_service.py`
- `app/routers/push_notification_routes.py`
- `app/schemas/push_notification_schema.py`
- `app/services/notification_service.py`
- `app/core/config.py`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `tests/test_20_firebase_push_service.py`
- `tools/firebase-web-test/firebase_token_test.html`
- `tools/firebase-web-test/firebase-messaging-sw.js`
- `docs/STEP_28_FIREBASE_PUSH.md`

Tables added:

- None.

Tables used:

- `users`
- `device_tokens`
- `notification_preferences`
- `notifications`

Configuration:

```env
FIREBASE_ENABLED=true
FIREBASE_CREDENTIALS_PATH=firebase-service-account-local.json
FIREBASE_CREDENTIALS_JSON=
```

Important security rule:

- `firebase-service-account-local.json` is a secret Firebase Admin SDK service-account file and must never be committed.
- Web Firebase config and VAPID public key are used for browser testing; they are not the same as the backend private service-account JSON.
- Do not log or commit Firebase private keys, JWTs, access tokens, Google tokens, or real user tokens.

Current behavior:

- Firebase status endpoint reports whether sending is enabled and configured.
- Test push endpoint sends a push to the authenticated current user.
- Push sender reads active `device_tokens` for the target user.
- Push sender checks `notification_preferences`, including `push_enabled` and notification-type-specific fields.
- Push sender skips cleanly when Firebase is disabled, credentials are missing, no token exists, or user preferences disable push.
- Push sender uses Firebase Admin SDK when enabled and configured.
- Invalid/unregistered tokens are deactivated when Firebase returns invalid-token errors.
- In-app notifications remain the primary record; push is best-effort.

Testing:

- Step 28 test file: `tests/test_20_firebase_push_service.py`.
- User confirmed isolated Step 28 result: `5 passed`.
- User confirmed full regression result: `129 passed`.
- User confirmed manual Swagger Firebase result:

```json
{
  "status": "sent",
  "detail": "Push notification sent successfully.",
  "sent_count": 1,
  "skipped_count": 0,
  "failed_count": 0,
  "deactivated_tokens": 0
}
```

Manual web test helper:

- Serve `tools/firebase-web-test` locally, usually on port `5500`.
- Open `http://127.0.0.1:5500/firebase_token_test.html`.
- Paste Firebase web app config and VAPID public key.
- Generate a real browser FCM token.
- Register the token in Planora.
- Send `/push-notifications/test` from Swagger or from the page.

## Step 29 - Alembic Migration Setup

Purpose:

- Stop manual PostgreSQL schema drift.
- Add versioned migrations without recreating the existing live schema.
- Keep FastAPI feature logic and authentication behavior unchanged.

Files added/updated:

- `requirements.txt` with Alembic.
- `alembic.ini`.
- `alembic/env.py`.
- `alembic/script.py.mako`.
- `alembic/versions/2bf54f983173_baseline_existing_planora_schema.py`.
- `alembic/versions/7562179d6e8d_add_password_reset_expiry_check.py`.

Current migration chain:

- `2bf54f983173` - empty baseline for the existing Planora schema.
- `7562179d6e8d` - adds `chk_password_reset_codes_expiry` on `password_reset_codes` with `CHECK (expires_at > created_at)`.

Configuration:

- `alembic/env.py` reads `settings.database_url` from `app.core.config`.
- `alembic/env.py` imports `app.models` so all SQLAlchemy models are registered.
- `target_metadata = Base.metadata` from `app.db.base`.
- `alembic.ini` leaves `sqlalchemy.url` blank because runtime config comes from `settings.database_url`.

Existing live database rule:

- Do not run migrations that create all existing tables.
- For an existing database that already matches the current schema, use Alembic stamping instead of replaying table-creation history.
- If the live DB already has `chk_password_reset_codes_expiry`, `python -m alembic stamp head` marks it current.
- If the live DB does not yet have `chk_password_reset_codes_expiry`, stamp the baseline revision first, then upgrade to head:

```powershell
python -m alembic stamp 2bf54f983173
python -m alembic upgrade head
```

Future schema rule:

- New schema changes should be represented as Alembic revisions.
- Avoid editing PostgreSQL schema manually except for emergency repair with a matching follow-up migration.

Step 29 verification from this Codex run:

- `python -m compileall app tests` passed.
- Plain `python -m pytest -x -v` could not run because the system Python interpreter did not have pytest installed.
- `.\venv\Scripts\python.exe -m pytest -x -v` completed with `4 passed, 125 skipped`; DB-backed tests skipped because `TEST_DATABASE_URL` was not set for this run.
- `.\venv\Scripts\python.exe -m alembic history` showed baseline -> password reset expiry check.
- `.\venv\Scripts\python.exe -m alembic heads` showed `7562179d6e8d` as the single head.

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

- Apply or stamp the Step 29 Alembic migration chain on live databases as described above.
- Treat `database/database_schema.sql`, if kept, as reference-only; Alembic is now the migration source of truth.
- Ruff is not installed yet; lint cleanup remains manual unless the project adds Ruff later.

Verification SQL:

```sql
SELECT conname
FROM pg_constraint
WHERE conname = 'chk_password_reset_codes_expiry';
```

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
python -m pytest tests/test_18_push_notifications_api.py -v
python -m pytest tests/test_19_cors_api.py -v
python -m pytest tests/test_20_firebase_push_service.py -v
python -m pytest --collect-only -q
python -m pytest --cov=app --cov-report=term-missing
python -m compileall app tests
python -m pip check
```

Future testing rule:

- Every backend feature step should include pytest tests before the step is considered done.
- Test files should be created through CMD/PowerShell commands by default, not only pasted as manual file content.
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions.
- Keep using `python -m pytest -x -v` as the first full regression check.
- After `-x` passes, run `python -m pytest -v` for the final full result.

## Roadmap From Here

Immediate next actions:

1. Apply or stamp the Alembic migration chain on the live development database.
2. Firebase Storage for attachments can be a later separate step if file storage becomes urgent.
3. Continue frontend/admin dashboard/mobile integration using the completed backend APIs.
4. Real AI API integration hardening can be improved later without changing API contracts.
5. Add Ruff/linting cleanup when ready.
6. Keep Docker as final polish after the core system is stable.

Next feature/polish candidates:

- Firebase Storage for attachments.
- Admin/notification polish.
- Frontend/mobile integration.
- Real AI API integration hardening.
- Tests/security cleanup/Ruff.
- Docker and deployment polish after the core system is stable.

## User Preference

- When the user says `done` or gives a test result after a backend step, update `docs/PLANORA_CONTEXT.md`.
- Always create new test files using CMD/PowerShell file-creation commands by default.
- Do not provide long PowerShell test scripts by default unless they are needed for creating files or the user explicitly requests them.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them.
- Keep Docker as final polish after core system features are stable.
- Keep this file as the main Planora project memory inside VS Code/Codex so the chat memory does not become too large.
