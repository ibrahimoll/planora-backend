# Planora Backend Context

Last updated: 2026-05-19

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, local rule-based AI with optional Gemini provider configuration, explicit CORS/frontend-mobile integration, Firebase Cloud Messaging real push sending, manual Firebase web-push testing helpers, and Alembic migrations.

Frontend/admin stack: separate Next.js admin dashboard repository using the existing FastAPI backend, protected admin auth, shared API client, dark SaaS dashboard UI, real backend data, and no fake admin telemetry.

Repositories:

- Backend: `ibrahimoll/planora-backend`
- Admin dashboard frontend: `ibrahimoll/planora-admin-dashboard`

## Current Verified Status

Latest confirmed clean full regression result:

- `129 passed`
- Confirmed on 2026-05-19 after the small scoped security/optimization/cleanup pass across backend and admin dashboard.
- Backend `python -m compileall app tests`: passed.
- Backend Alembic head remains `7562179d6e8d`; history is valid.
- Frontend `npm run lint`: passed with one existing `img` performance warning in `settings/page.tsx`.
- Frontend `npm run build`: passed.
- Browser smoke: protected `/dashboard` redirects to `/login`; no console errors reported.
- Previous confirmed clean full regression result was `129 passed` after Step 29 Alembic Migration Setup.
- Previous confirmed clean full regression result was `129 passed` after Step 28 Firebase Cloud Messaging real push sending.
- Test database requirement: `TEST_DATABASE_URL` must point to `planora_test_db`, not the normal development database.

Important verification commands:

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
python -m pytest -v
```

## Completed Backend Steps

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

## Admin Backend Capabilities

Critical admin actions create `admin_logs` rows.

### Dashboard Overview

Endpoints:

- `GET /admin/dashboard/overview`
- `GET /admin/dashboard/recent-activity`
- `GET /admin/logs`

Admin can view system statistics, recent activity, and audit logs.

### Admin User Management

Endpoints:

- `GET /admin/users`
- `GET /admin/users/{user_id}`
- `GET /admin/users/{user_id}/activity`
- `PATCH /admin/users/{user_id}/deactivate`
- `PATCH /admin/users/{user_id}/activate`
- `PATCH /admin/users/{user_id}/role`

Supported `/admin/users` filters:

- `role`
- `is_active`
- `is_email_verified`
- `search`
- `limit`
- `offset`

Protections:

- Admin cannot deactivate self.
- Admin cannot remove own admin role.
- Admin cannot remove/deactivate the last active verified admin.

### Admin Project Oversight

Endpoints:

- `GET /admin/projects`
- `GET /admin/projects/{project_id}`
- `PATCH /admin/projects/{project_id}/status`

Supported filters:

- `limit`
- `offset`
- `project_type`
- `status`
- `owner_id`
- `team_id`
- `search`

Important contract:

- Status filter query parameter is `status`.
- Project type query parameter is `project_type`.
- Status update body is `{ "status": "in_progress" }` using one of `not_started`, `in_progress`, `completed`, `on_hold`, or `cancelled`.
- Search currently matches project `title` and `description`.

### Admin Task Oversight

Endpoints:

- `GET /admin/tasks`
- `GET /admin/tasks/{task_id}`
- `PATCH /admin/tasks/{task_id}/status`
- `PATCH /admin/tasks/{task_id}/assignment`

Supported filters:

- `limit`
- `offset`
- `status`
- `priority`
- `project_id`
- `assigned_to`
- `created_by`
- `overdue`
- `unassigned`
- `search`

### Admin Risk Center

Endpoints:

- `GET /admin/risk/summary`
- `GET /admin/risk/high-risk-projects`

Admin can view system-level risk summary and list high-risk projects using latest risk records.

### Admin Reports Center

Endpoints:

- `GET /admin/reports/system-summary`
- `GET /admin/reports/projects-summary`
- `GET /admin/reports/users-summary`

Admin can generate JSON summary reports for system, projects, and users.

### Notifications and Push Notifications

Notification endpoints:

- `GET /notifications`
- `GET /notifications/unread-count`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/read-all`
- `DELETE /notifications/{notification_id}`

Push endpoints:

- `POST /push-notifications/device-tokens`
- `GET /push-notifications/device-tokens`
- `PATCH /push-notifications/device-tokens/{device_token_id}/deactivate`
- `GET /push-notifications/preferences`
- `PATCH /push-notifications/preferences`
- `GET /push-notifications/status`
- `POST /push-notifications/test`

Firebase private service-account credentials must never be committed or exposed in the frontend.

## AI / Intelligence Features

AI Project Planning MVP:

- Saves generated plans in `ai_plans`.
- Can optionally create tasks from generated plans.
- Uses local deterministic/rule-based logic named `local_rule_based_v1`.

Risk Analysis / Delay Prediction MVP:

- Saves generated risk snapshots in `risk_analysis`.
- Calculates risk using project deadline, task completion, overdue tasks, blocked tasks, and remaining estimated hours.
- Saved high-risk analyses create in-app `risk` notifications.
- Push sending can also be triggered when a notification is created and Firebase/prefs/tokens allow it.
- Uses local deterministic/rule-based logic.

Smart Scheduling MVP:

- Saves generated schedule snapshots in `smart_schedules`.
- Can preview schedules without modifying tasks.
- Can optionally apply generated schedules by updating incomplete task due dates.
- Uses local deterministic balanced scheduling strategy.

AI Chat Assistant MVP:

- `POST /projects/{project_id}/chat`
- `GET /projects/{project_id}/chat`
- `POST /teams/{team_id}/projects/{project_id}/chat`
- `GET /teams/{team_id}/projects/{project_id}/chat`

Current behavior:

- Active verified users can chat with AI for personal projects they own.
- Team project members can chat with AI for team projects they belong to.
- Non-members are blocked from team project chat.
- User messages are saved in `chat_messages` with `sender_type = 'user'` and `sender_id` set to the current user.
- AI messages are saved in `chat_messages` with `sender_type = 'ai'` and `sender_id = NULL`.

AI provider status:

- Default AI provider is `local`.
- `.env.example` documents `AI_PROVIDER=local`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`, and `GEMINI_TIMEOUT_SECONDS=15`.
- Gemini provider code is optional and falls back to local AI if provider/API configuration fails.
- Do not log full prompt bodies, raw model responses, tokens, API keys, passwords, JWTs, or private user data.

Future AI integration rule:

- Replace only generator/analyzer/scheduler/chat-provider logic inside service files while keeping the same API contracts.

## Step 29 — Alembic Migration Setup

Purpose:

- Stop manual PostgreSQL schema drift.
- Add versioned migrations without recreating the existing live schema.
- Keep FastAPI feature logic and authentication behavior unchanged.

Current migration chain:

- `2bf54f983173` — empty baseline for the existing Planora schema.
- `7562179d6e8d` — adds `chk_password_reset_codes_expiry` on `password_reset_codes` with `CHECK (expires_at > created_at)`.

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
- Review every Alembic autogenerated migration manually before running it.

## Step 30 — Admin Dashboard Integration Foundation

Status: largely complete and verified, with remaining polish items only.

### Admin Authentication Foundation — Completed

Completed:

- Separate Next.js admin dashboard frontend repository exists.
- `/` redirects to `/login`.
- `/login`, `/forgot-password`, and `/reset-password` exist.
- Admin login uses existing `POST /auth/login` with `application/x-www-form-urlencoded` fields `username` and `password`.
- Frontend stores the Planora JWT in `planora_admin_token`.
- Frontend attaches the token through `lib/api.ts` on protected requests.
- Login calls `/auth/me` and requires `role = admin` before allowing dashboard access.
- Non-admin users are blocked and token is cleared.
- Protected `401`/`403` responses clear token and redirect to `/login` outside public auth pages.
- Logout clears token and redirects to `/login`.
- Forgot/reset password pages are connected to backend auth flow.

### Approved Admin Dashboard Style

- Clean dark SaaS admin dashboard.
- Planora/AI-aware, but not cyber-template or overdone AI UI.
- Use real backend data rather than fake charts or fake telemetry.
- Use clear human admin labels.
- Cyan/teal is the main accent color.
- Purple is only a restrained secondary/status color.
- Avoid excessive glow, glassmorphism, floating orbs, fake dashboard mockups, meaningless AI/cyber wording, fake testimonials, or decorative animations.
- Keep useful motion only: page transitions, subtle reveal sections, hover states, active sidebar state, dropdown animation, and clean loading states.
- Do not change the logo style unless explicitly requested.

### Current Dashboard Shell Rules

- Sidebar is fixed/full-height by layout, not dependent on sticky behavior.
- Topbar remains visible while scrolling.
- The browser/page itself should not scroll for dashboard routes; only the right dashboard content area scrolls.
- `ProtectedAdminLayout` uses an `h-screen overflow-hidden` root and a scrollable content region.
- `dashboard-scale` should be applied to the dashboard content region only, not around the topbar.
- Avoid custom inner scrollbars inside cards unless absolutely necessary.

### Completed Admin Dashboard Pages

Current admin-dashboard routes/pages:

- `/dashboard` — overview dashboard using real admin overview and recent activity APIs.
- `/dashboard/users` — user management with search, filters, limit/offset pagination, detail, activity load-more, activate/deactivate, promote/demote, and self-action protections.
- `/dashboard/projects` — project oversight with grouped vertical portfolio view, backend filters, limit/offset pagination, detail panel, and status update.
- `/dashboard/tasks` — task oversight with backend filters, limit/offset pagination, grouped workload, detail, status update, assignment/unassignment.
- `/dashboard/risk` — risk center using risk summary and high-risk project APIs.
- `/dashboard/reports` — reports center with System Summary, Projects Summary, Users Summary, and Project Report tabs.
- `/dashboard/notifications` — notification center with list, unread count, filters/search, mark one read, mark all read, and delete.
- `/dashboard/admin-logs` — audit log page with filters, user labels, limit/offset pagination.
- `/dashboard/settings` — profile, profile picture, password change, Firebase push status, notification preferences, saved device tokens, token deactivation, and safe test push sending.

Sidebar currently includes:

- Overview
- Users
- Projects
- Tasks
- Risk
- Reports
- Notifications
- Admin Logs
- Settings

### Admin Dashboard Parity Status

Main backend admin capabilities are covered in the frontend.

Covered:

- Admin dashboard overview.
- Recent activity.
- Users list/filter/detail/activity/actions, including `limit`, `offset`, `role`, `is_active`, `is_email_verified`, and `search`.
- Selected user activity, including `limit`, `offset`, and load-more behavior.
- Projects list/filter/detail/status update, including `limit`, `offset`, `project_type`, `status`, `owner_id`, `team_id`, and `search`.
- Tasks list/filter/detail/status update/assignment update, including `limit`, `offset`, `status`, `priority`, `project_id`, `assigned_to`, `created_by`, `overdue`, `unassigned`, and `search`.
- Risk summary and high-risk projects.
- Admin reports summaries.
- Project reports.
- Notifications list/read/delete.
- Admin logs with filters and pagination.
- Settings/profile/password/profile picture.
- Push notification status/preferences/device tokens and test push sending.

Marked completed from frontend verification:

- Step 30.10 - Admin Tasks Page.
- Step 30.11 - Risk Center Page.
- Step 30.12 - Reports Page.
- Activity / Notifications page.
- Admin Logs page.
- Admin settings page with push notification settings.

### Remaining Admin Dashboard Polish

- Real browser FCM token registration should remain a TODO unless safe public Firebase config and VAPID handling are added.
- Do not expose destructive `DELETE /profile` account deletion in admin dashboard by default; it needs a dedicated safe design and confirmation flow first.
- Backend list endpoints return arrays without total counts, so frontend pagination uses `limit`, `offset`, and "next disabled when returned rows are fewer than the page size."
- Optional future polish: saved report export history, richer audit-log actor/target labels from backend joins, broader browser smoke tests with seeded admin data, and total-count metadata if better pagination UX is needed.
- Replace the settings profile `<img>` with Next Image/custom loader later only if worth the complexity.

## Cleanup / Optimization Pass — 2026-05-19

A small scoped cleanup pass was completed across backend and admin dashboard.

Files changed in that pass:

- `app/services/admin_risk_report_service.py`
- `app/services/password_reset_service.py`
- `lib/api.ts`
- `lib/adminProfileSync.ts`
- `app/dashboard/settings/page.tsx`
- `app/globals.css`
- `src/components/dashboard/Topbar.tsx`

Changes:

- Backend admin projects summary avoids per-project task count queries and calculates completion with one aggregate query.
- Backend password reset lookup deterministically selects the latest active code with a tie-breaker and `limit(1)`.
- Frontend API base URL resolution is centralized through `lib/api.ts`.
- Old dashboard topbar logout now clears the real admin token key through the shared auth helper.
- Removed global smooth-scroll CSS that caused a Next.js console warning.
- No endpoint mismatches found for admin logs, notifications, push notification settings, or admin reports.

Verification:

- Backend `python -m compileall app tests`: passed.
- Backend global pytest was blocked because global Python lacked pytest.
- Backend venv pytest without `TEST_DATABASE_URL`: `4 passed, 125 skipped`.
- Backend venv pytest with `TEST_DATABASE_URL` configured: `129 passed`.
- Backend Alembic via project venv: head is `7562179d6e8d`; history is valid.
- Frontend `npm run lint`: passed with one existing `<img>` performance warning in settings.
- Frontend `npm run build`: passed.
- Browser smoke: protected `/dashboard` redirects to `/login`; no console errors.

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
- Test files should be created through CMD/PowerShell commands by default.
- Do not rely on pasted-only test content when a command-created test file is expected.
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions.
- Keep using `python -m pytest -x -v` as the first full regression check.
- After `-x` passes, run `python -m pytest -v` for the final full result.

## Roadmap From Here

Recommended next order:

1. Final admin dashboard polish and manual demo testing.
2. Step 31 — Mobile/User Frontend Integration Foundation.
3. Step 32 — Firebase Storage for Attachments.
4. Real AI API integration hardening.
5. Tests/security cleanup/Ruff.
6. Docker and deployment polish after the core system is stable.

Firebase Storage for attachments remains useful, but it is lower priority unless attachment hosting becomes urgent. It should come after frontend/admin/mobile integration because it is more of an infrastructure polish step than a demo-critical feature.

## Future Landing Page Design Rules

Prompt1:
Remove every gradient, glassmorphism effect, and purple-to-blue background from my landing page. Replace with one flat background color and a single accent color.

Prompt2:
Rewrite all copy on my landing page in plain human English. No "empower," "unleash," "revolutionize," "supercharge," or emoji. Write like a real person explaining the product to a friend.

Prompt3:
Replace the three-feature-cards-in-a-row section with something that proves the product is real: an actual product screenshot, a short demo clip, or a concrete number/result. No generic icons.

Prompt4:
Pick one real font, not the default, set line-height to 1.5-1.6 for body text, and fix all spacing so sections have consistent vertical rhythm. Remove cramped or uneven padding.

Prompt5:
Audit my entire landing page and remove anything that exists only because it looked cool in a Tailwind demo: floating orbs, fake dashboard mockups, fake testimonials, decorative blurs, and unused animations.

These prompts are mandatory for the future public Planora landing page. When a landing page or public website is created, Codex must apply these rules before styling polish. Do not skip these rules just because the landing page does not exist yet. The landing page should be simple, credible, and human. The admin dashboard remains a separate dark SaaS/admin interface.

## User Preference

- When the user says `done` or gives a test result after a backend step, update `docs/PLANORA_CONTEXT.md`.
- Always create new test files using CMD/PowerShell file-creation commands by default.
- Do not provide long PowerShell test scripts by default unless they are needed for creating files or the user explicitly requests them.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them.
