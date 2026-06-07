# Planora Project Context

Last updated: 2026-06-03

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- A mobile app for users/team members.
- A separate web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, project-scoped AI chat with local deterministic fallbacks and optional Gemini LLM provider integration, explicit CORS/frontend-mobile integration, Firebase Cloud Messaging push sending, automatic deadline reminder scheduling, Alembic migrations, total-count pagination metadata, and saved report export history.

Admin dashboard stack: separate Next.js repository using the FastAPI backend, protected admin auth, shared API client, dark SaaS admin UI, real backend data, browser Firebase Cloud Messaging token registration, and no fake telemetry.

Mobile app stack/status: Flutter mobile app in `ibrahimoll/planora-mobile`. Mobile auth integration, reset-password link flow, AuthGate session persistence, Firebase web hosting, and the first real Home dashboard UI are now implemented/polished. Mobile is now moving from auth/dashboard shell polish into real feature screens and backend data integration for projects, tasks, notifications, AI chat, profile/settings, and team collaboration.

Repositories:

- Backend: `ibrahimoll/planora-backend`
- Admin dashboard frontend: `ibrahimoll/planora-admin-dashboard`
- Mobile app: `ibrahimoll/planora-mobile`

## Current Verified Status

Latest confirmed status:

- Backend Step 31 Automatic Notification Scheduler is complete.
- Backend Step 32 Backend Total-Count Pagination is complete.
- Backend Step 33 Saved Report Export History is complete.
- Backend AI Chat Assistant has a project-only scope guard: project/greeting questions are allowed; unrelated questions such as weather are blocked before the LLM provider is called.
- Gemini provider was configured locally through `.env` and verified manually by the user. The real `GEMINI_API_KEY` must stay local and must never be committed.
- Backend Alembic head is `8b2c6d9f0a11`.
- Backend focused Step 33 test file `tests/test_22_report_export_history_api.py` passed with `3 passed`.
- Backend full regression passed after Step 33 with `139 passed`.
- Backend full regression passed after AI chat scope guard/Gemini verification with `140 passed`.
- Backend `python -m compileall app tests` passed after Step 33.
- Deployment milestone: user has deployed the backend, PostgreSQL database, admin dashboard site, and mobile web preview/hosting flow.
- Admin dashboard final polish pass is complete.
- Admin dashboard latest local verification after browser FCM work: `npm run lint` reported `0 errors`; `npm run build` passed.
- Browser FCM token registration was implemented and tested successfully on web/laptop: browser permission prompt, real Firebase token registration, saved `web` device token, and test push notification received.
- Temporary admin-dashboard patch scripts were removed from the frontend repo.

## Latest Mobile Status — 2026-06-03

Reported latest local mobile commit:

- `1247cc5 Polish auth session and home dashboard`

This commit was reported as committed locally in `planora-mobile`. Push status should be checked with `git status` / `git log origin/main..HEAD` before assuming it is on GitHub.

Completed/updated mobile work:

- Mobile onboarding UI is complete in light/dark style and navigates to login/register.
- Mobile login UI is complete and responsive.
- Login supports email/username input if backend supports it.
- Login now routes successful auth back through AuthGate instead of bypassing the app-level session controller.
- Mobile register UI is complete and responsive.
- Register password rules card appears when the password field is focused and updates live.
- Mobile email verification UI is complete and responsive.
- Forgot password uses password reset link flow, not reset code flow.
- `ForgotPasswordScreen` calls backend forgot-password API and routes to `ResetLinkSentScreen`.
- `ResetLinkSentScreen` has the auth/logo header removed per design request and says reset link, not reset code.
- Public reset links open `/reset-password?email=...&token=...` directly into `ResetPasswordScreen`.
- `ResetPasswordScreen` exists and was manually reported working.
- `/reset-password` direct route is preserved in `main.dart` before AuthGate normal routing.
- Reset email/token from URL are trimmed/safely handled.
- `AuthGate` is implemented.
- AuthGate keeps valid saved JWT sessions and routes to Home automatically.
- AuthGate clears saved JWT only on real auth rejection; transient network/server failures should not immediately wipe a valid session.
- AuthGate now has retry/sign-out UI for session-check failures.
- Logout clears token and returns to onboarding/auth state cleanly.
- Token storage is implemented through `TokenStorage`.
- Google auth API helper matching backend `/auth/google` was added in mobile API layer.
- `AppConfig` handles `PLANORA_API_URL` using `--dart-define` and should trim trailing slashes.
- Firebase hosting for mobile web was initialized using `build/web` as public directory and SPA rewrite to `index.html`.
- Render CORS allowed origins were updated to include local web ports/LAN/Firebase/Vercel URLs as needed.

Mobile Home dashboard status:

- Temporary Home screen was replaced by a real first dashboard UI.
- Header includes greeting based on device time, first name, search icon, notification icon, and avatar actions.
- Notification dot should appear only when unread notifications exist.
- Dashboard includes Project Overview, Quick Actions, My Projects, Upcoming Tasks, and bottom navigation.
- Quick Actions were restyled to compact cards matching the reference: New Project, New Task, Invite Team, View Reports.
- My Projects icons were polished with modern project-logo cards.
- Dark mode text/readability was improved; user preference is that dark-mode readable text should be white/near-white.
- Bottom navigation currently uses Planora style with Home, Projects, center Planora AI, Tasks, Calendar.
- Profile was removed from bottom navigation; profile/logout/theme actions can stay accessible from avatar/header.
- Bottom navigation requirements: keep center-docked Planora AI button, Planora purple selected state, smooth sliding selected animation, no random yellow/orange colors.
- User rejected weak/jumpy animation; smooth sliding active state is required.
- The `animated_bottom_navigation_bar` package is installed and can be used where useful, but style and smooth sliding behavior matter more than package choice.
- Android/web overscroll stretch should be avoided across the mobile app where possible.

Mobile verification reported after Codex audit:

- `flutter pub get` passed.
- `flutter analyze` passed with zero issues.
- No `test` or `integration_test` directories existed, so no tests were run.
- Release web preview rendered cleanly with no browser warnings.
- Live login/logout/reset manual checks were not run by Codex because no real credentials/reset link were available in that workspace.

Manual mobile checks still needed:

1. Launch app with no token -> onboarding/login appears.
2. Login with real credentials -> Home opens.
3. Refresh app -> Home opens through AuthGate if token is valid.
4. Kill/reopen app or reload browser -> valid session persists.
5. Logout -> onboarding/login appears and token is cleared.
6. Forgot password -> reset link email arrives.
7. Reset link -> `ResetPasswordScreen` opens and password can be changed.
8. Login with new password works.
9. Toggle dark mode -> all Home/auth text is readable.
10. Bottom nav: Home/Projects/Planora AI/Tasks/Calendar selected states animate smoothly.
11. Small mobile widths -> no overflow/clipping.
12. Scroll to top/bottom -> no ugly stretch/overscroll behavior.

## Important Mobile Files

Auth/core files:

- `lib/main.dart`
- `lib/core/config/app_config.dart`
- `lib/core/network/api_client.dart`
- `lib/core/network/api_exception.dart`
- `lib/core/storage/token_storage.dart`
- `lib/features/auth/auth_gate.dart`
- `lib/features/auth/data/auth_api.dart`
- `lib/features/auth/models/auth_models.dart`

Auth UI files:

- `lib/features/onboarding/onboarding_screen.dart`
- `lib/features/login/login_screen.dart`
- `lib/features/register/register_screen.dart`
- `lib/features/email_verification/email_verification_screen.dart`
- `lib/features/forgot_password/forgot_password_screen.dart`
- `lib/features/reset_password/reset_password_screen.dart`
- Shared auth responsive helper: `lib/features/auth/shared/auth_responsive_metrics.dart`
- Shared auth widgets: `lib/features/auth/shared/auth_widgets.dart`

Home/dashboard files:

- `lib/features/home/home_screen.dart`
- `lib/features/home/widgets/home_bottom_nav.dart`

Theme/assets:

- `lib/core/theme/planora_theme.dart`
- Google logo asset: `assets/icons/google_logo.svg`
- Email verification assets:
  - `assets/images/email_verification_light.png`
  - `assets/images/email_verification_dark.png`
- Forgot password/reset link assets:
  - `assets/images/forgot_password_light.png`
  - `assets/images/forgot_password_dark.png`
  - `assets/images/reset_link_sent_light.png`
  - `assets/images/reset_link_sent_dark.png`

## Mobile App Current UI Direction

The mobile UI should follow the clean, modern, friendly, professional Planora light/dark purple identity:

- Primary purple gradient buttons.
- Rounded white/light cards in light mode.
- Dark navy/slate surfaces in dark mode.
- Soft lavender/purple backgrounds and accents.
- Auth screens use Planora logo and `AI-POWERED PROJECT PLANNING` pill where appropriate.
- Reset link sent/check-email screen should not show the logo/AI pill per latest design request.
- Responsive layouts using `LayoutBuilder`, `SingleChildScrollView`, max content width, keyboard-safe scrolling, and `AuthResponsiveMetrics`.
- Auth screens should support small phones, normal phones, tablet/web widths, and keyboard-open states.
- Home dashboard should match the provided modern reference: greeting header, Project Overview, Quick Actions, My Projects, Upcoming Tasks, and bottom navigation.
- Bottom navigation style should keep Planora colors, center Planora AI button, and smooth sliding selected animation.

## Mobile Backend Integration Notes

Backend auth already supports:

- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/resend-verification-code`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /auth/login`
- `POST /auth/google`
- `GET /auth/me`

Important auth/API rules:

- Login uses form data with fields `username` and `password`.
- The `username` field in login can contain email or username if backend supports both.
- `/auth/me` requires the Planora JWT access token, not a Google ID token.
- Google ID token is only submitted to `/auth/google`; backend returns a Planora JWT.
- Do not log tokens, reset tokens, passwords, Google ID tokens, Gmail app passwords, API keys, or secrets.
- Token storage should go through `TokenStorage` only.
- `token_storage.dart` should use `const FlutterSecureStorage()` directly. Do not use deprecated `AndroidOptions(encryptedSharedPreferences: true)`.
- Apple login should stay UI-only/coming-later unless Apple Developer setup is available.
- Backend register requires `username`; current mobile register UI historically had no username field, so either generate username from email locally or update backend to auto-generate username before full registration integration.

## Next Recommended Mobile Steps

Recommended order after auth/dashboard polish:

1. Manually verify the real auth lifecycle with deployed backend:
   - login, refresh, AuthGate persistence, logout, forgot-password email, reset-password link, login with new password.
2. Push local commit `1247cc5` to `origin/main` if not already pushed.
3. Build real Projects flow:
   - project API models/client.
   - projects list screen.
   - project detail screen.
   - create project screen.
   - connect Home "My Projects" and "New Project" quick action to real data/navigation.
4. Build real Tasks flow:
   - task models/client.
   - tasks list screen.
   - task detail screen.
   - create/update/complete task interactions.
   - connect Home "Upcoming Tasks" and "New Task" quick action.
5. Build Notifications screen and unread count connection:
   - connect header bell unread dot to `GET /notifications/unread-count`.
   - list notifications from `GET /notifications`.
   - support mark read/read all/delete.
6. Build Planora AI screen from center bottom button:
   - project-scoped AI chat UI.
   - later connect to backend AI chat endpoints.
7. Build Profile/Settings screens:
   - profile details.
   - edit profile.
   - change password.
   - theme/settings.
8. Build Team Members / collaboration screens.
9. Add tests after screens stabilize.
10. Final cleanup/optimization after feature completion, not before.

## Important Backend Verification Commands

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
alembic upgrade head
alembic current
alembic history
python -m pytest -x -v
python -m pytest -v
python -m compileall app tests
```

## Important Admin Dashboard Verification Commands

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\admin-dashboard
git pull origin main
npm run lint
npm run build
```

## Important Mobile Verification Commands

```powershell
cd C:\Users\Ibrahim\Documents\Planora\mobile
git pull origin main
flutter pub get
flutter analyze
flutter run -d chrome --web-port 8080
```

Run mobile against deployed backend:

```powershell
flutter run -d chrome --web-port 8080 --dart-define=PLANORA_API_URL=https://planora-api-dqmv.onrender.com
```

Build/deploy mobile web to Firebase:

```powershell
flutter build web --dart-define=PLANORA_API_URL=https://planora-api-dqmv.onrender.com
firebase deploy
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
24.1. Project-scoped AI chat guard and local Gemini provider verification.
25. Productivity Insights Center.
26. Push Notification Foundation.
27. CORS / Frontend-Mobile Integration.
28. Firebase Cloud Messaging real push sending.
29. Alembic Migration Setup.
30. Admin Dashboard Integration and Final Polish.
31. Automatic Notification Scheduler for due-soon/overdue task reminders and automatic push delivery.
32. Backend Total-Count Pagination for admin users/projects/tasks/admin logs.
33. Saved Report Export History.

## Latest AI Project Planning State - 2026-06-07

- Mobile-friendly AI planning endpoints are available at `POST /projects/{project_id}/ai-plan/generate` and `POST /teams/{team_id}/projects/{project_id}/ai-plan/generate`.
- The endpoint stores a row in `ai_plans`, can create real rows in `tasks`, and returns `project_id`, `plan_id`, `summary`, `tasks_created`, and created task summaries.
- The current generator uses deterministic local fallback logic (`local_rule_based_v1`) and does not require mobile-side AI secrets.
- Older `/ai-plans` routes remain available for plan history and compatibility.
- Contract details and examples are documented in `docs/AI_PROJECT_PLANNING.md`.

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
- `report_exports`

Optional future tables:

- Firebase push delivery log table if delivery audit/history is needed.

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

## Preferred Mobile Coding Workflow

- Explain the purpose of the current step in English first.
- Then provide code one function/class at a time.
- For each function/class, explain:
  1. Function/class name.
  2. What it does.
  3. Why Planora needs it.
  4. The exact code for that function/class.
  5. What to test before continuing.
- Avoid giving huge multi-file code dumps unless explicitly requested.
- When the user asks for direct repo changes, make targeted commits and tell the user exactly what to pull/test.
- Keep checking `ibrahimoll/planora-backend` for endpoint contracts when mobile behavior depends on backend responses.
