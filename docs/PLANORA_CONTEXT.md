# Planora Project Context

Last updated: 2026-05-19

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- A mobile app for users/team members.
- A separate web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, local rule-based AI with optional Gemini provider configuration, explicit CORS/frontend-mobile integration, Firebase Cloud Messaging push sending, and Alembic migrations.

Admin dashboard stack: separate Next.js repository using the FastAPI backend, protected admin auth, shared API client, dark SaaS admin UI, real backend data, and no fake telemetry.

Repositories:

- Backend: `ibrahimoll/planora-backend`
- Admin dashboard frontend: `ibrahimoll/planora-admin-dashboard`

## Current Verified Status

Latest confirmed status:

- Backend full regression previously confirmed: `129 passed` with `TEST_DATABASE_URL` configured.
- Backend `python -m compileall app tests`: passed in the latest cleanup pass.
- Backend Alembic head remains `7562179d6e8d`; migration history is valid.
- Admin dashboard final polish pass is complete.
- Admin dashboard latest local verification: `npm run lint` reported `0 errors`; `npm run build` passed.
- Temporary admin-dashboard patch scripts were removed from the frontend repo.

Important backend verification commands:

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
python -m pytest -v
python -m compileall app tests
python -m alembic current
python -m alembic history
```

Important admin dashboard verification commands:

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\admin-dashboard
git pull origin main
npm run lint
npm run build
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
30. Admin Dashboard Integration and Final Polish.

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

Optional future tables:

- Firebase push delivery log table if delivery audit/history is needed.
- Report export history table if saved/download history is needed.

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
- Inactive or unverified users are blocked by `get_current_active_verified_user`.
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

Role systems are separate:

- Global user role: `users.role`: `user`, `admin`.
- Team membership role: `team_members.role`: `owner`, `admin`, `member`.
- Project membership role: `project_members.role`: `owner`, `manager`, `member`.

Changing a user to global admin gives access to admin dashboard routes but does not automatically modify team/project roles.

## Admin Backend Capabilities

Critical admin actions create `admin_logs` rows.

Dashboard overview:

- `GET /admin/dashboard/overview`
- `GET /admin/dashboard/recent-activity`
- `GET /admin/logs`

User management:

- `GET /admin/users`
- `GET /admin/users/{user_id}`
- `GET /admin/users/{user_id}/activity`
- `PATCH /admin/users/{user_id}/deactivate`
- `PATCH /admin/users/{user_id}/activate`
- `PATCH /admin/users/{user_id}/role`

User management protections:

- Admin cannot deactivate self.
- Admin cannot remove own admin role.
- Admin cannot remove/deactivate the last active verified admin.

Project oversight:

- `GET /admin/projects`
- `GET /admin/projects/{project_id}`
- `PATCH /admin/projects/{project_id}/status`

Task oversight:

- `GET /admin/tasks`
- `GET /admin/tasks/{task_id}`
- `PATCH /admin/tasks/{task_id}/status`
- `PATCH /admin/tasks/{task_id}/assignment`

Risk center:

- `GET /admin/risk/summary`
- `GET /admin/risk/high-risk-projects`

Reports center:

- `GET /admin/reports/system-summary`
- `GET /admin/reports/projects-summary`
- `GET /admin/reports/users-summary`

Notifications:

- `GET /notifications`
- `GET /notifications/unread-count`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/read-all`
- `DELETE /notifications/{notification_id}`

Push notifications:

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

AI provider status:

- Default AI provider is `local`.
- `.env.example` documents `AI_PROVIDER=local`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`, and `GEMINI_TIMEOUT_SECONDS=15`.
- Gemini provider code is optional and falls back to local AI if provider/API configuration fails.
- Do not log full prompt bodies, raw model responses, tokens, API keys, passwords, JWTs, or private user data.

Future AI integration rule:

- Replace only generator/analyzer/scheduler/chat-provider logic inside service files while keeping the same API contracts.

## Alembic Migration Setup

Purpose:

- Stop manual PostgreSQL schema drift.
- Add versioned migrations without recreating the existing live schema.
- Keep FastAPI feature logic and authentication behavior unchanged.

Current migration chain:

- `2bf54f983173` — empty baseline for the existing Planora schema.
- `7562179d6e8d` — adds `chk_password_reset_codes_expiry` on `password_reset_codes` with `CHECK (expires_at > created_at)`.

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
- Review every autogenerated migration manually before running it.

## Admin Dashboard Final Status

Status: complete for the main FYP admin-dashboard pass.

Completed pages:

- `/dashboard` — overview dashboard using real admin overview and recent activity APIs.
- `/dashboard/users` — user management with search, filters, pagination, detail, activity load-more, activate/deactivate, promote/demote, shared loading/empty states, and confirmation dialog for role/status actions.
- `/dashboard/projects` — project oversight with grouped portfolio view, filters, pagination, detail panel, status update, shared loading/empty states.
- `/dashboard/tasks` — task oversight with filters, pagination, grouped workload, detail, status update, assignment/unassignment, shared loading/empty states.
- `/dashboard/risk` — risk center using risk summary and high-risk project APIs, shared loading/empty states.
- `/dashboard/reports` — System Summary, Projects Summary, Users Summary, and Project Report tabs, shared loading/empty states.
- `/dashboard/notifications` — list, unread count, filters/search, mark one read, mark all read, delete, shared loading/empty states, confirmation dialog for delete.
- `/dashboard/admin-logs` — audit log filters, user labels, pagination, shared loading/empty states.
- `/dashboard/settings` — profile, profile picture, password change, Firebase push status, notification preferences, saved device tokens, token deactivation, and safe test push sending.

Admin dashboard shell/style status:

- Dark SaaS admin dashboard style is approved.
- Sidebar/topbar/logo/loading screen polish completed.
- Sidebar uses fixed/full-height dashboard layout behavior.
- Topbar remains visible while dashboard content scrolls.
- Temporary patch scripts were removed.
- Latest local admin-dashboard verification reported `npm run lint` with `0 errors` and `npm run build` passing.

Known intentional TODOs:

- Real browser FCM token registration remains future work unless safe public Firebase config and VAPID handling are added.
- Backend list endpoints still return arrays without total counts; frontend pagination uses `limit`, `offset`, and next disabled when returned rows are fewer than page size.
- Optional future polish: saved report export history, richer audit-log actor/target labels from backend joins, seeded browser smoke tests, and total-count metadata.

## Backend Security / Cleanup Review — 2026-05-19

Reviewed areas:

- FastAPI app setup and CORS/security headers.
- Pydantic settings and `.env.example` secret handling.
- JWT current-user and admin-user dependencies.
- Profile picture upload path handling and file validation.
- Admin user-management self/last-admin protections.
- Public DB health endpoint behavior.

Current assessment:

- No committed real secrets were found in the inspected config/example files.
- CORS origins are explicit and `.env.example` warns not to use `*` with credentialed auth headers.
- Protected routes use current active verified user and admin dependencies.
- Admin user-management protects self-deactivation, self-demotion, and last active verified admin removal.
- Profile picture upload uses extension/content-type allowlists, UUID stored names, a size limit, and path traversal checks.
- Security headers currently include `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.

Recommended next backend hardening items:

1. Run full backend regression again with `TEST_DATABASE_URL` after any future code changes.
2. Consider adding a production-only `Strict-Transport-Security` header when deployed behind HTTPS.
3. Consider rate limiting for login, resend verification, forgot password, reset password, and test push endpoints before public deployment.
4. Consider making `/health/db` production-safe by returning only a generic status and not exposing DB details beyond success/failure.
5. Consider adding CI for backend tests and frontend lint/build so GitHub can verify future pushes automatically.

## Regression Testing Rules

Standard local pytest command pattern:

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
python -m pytest -v
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
- Prefer API-level tests with `TestClient`, isolated PostgreSQL test database, disabled outbound email, and clear assertions.
- Keep using `python -m pytest -x -v` as the first full regression check.
- After `-x` passes, run `python -m pytest -v` for the final full result.

## Roadmap From Here

Recommended next order:

1. Backend final hardening items that are safe for FYP/demo scope.
2. Step 31 — Mobile/User Frontend Integration Foundation.
3. Step 32 — Firebase Storage for Attachments.
4. Real AI API integration hardening.
5. CI, Ruff, Docker, and deployment polish after the core system is stable.

Firebase Storage for attachments remains useful, but it is lower priority unless attachment hosting becomes urgent.

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

These prompts are mandatory for the future public Planora landing page. The admin dashboard remains a separate dark SaaS/admin interface.

## User Preference

- When the user says `done` or gives a test result after a backend step, update `docs/PLANORA_CONTEXT.md`.
- Always create new test files using CMD/PowerShell file-creation commands by default.
- Do not provide long PowerShell test scripts by default unless they are needed for creating files or the user explicitly requests them.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
- For backend feature steps, always include pytest tests and run/verify them.
