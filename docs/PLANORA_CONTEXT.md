# Planora Project Context

Last updated: 2026-06-01

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- A mobile app for users/team members.
- A separate web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.

Backend stack: FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, JWT auth, Google social login, SMTP email verification/reset, local file storage for development, project-scoped AI chat with local deterministic fallbacks and optional Gemini LLM provider integration, explicit CORS/frontend-mobile integration, Firebase Cloud Messaging push sending, automatic deadline reminder scheduling, Alembic migrations, total-count pagination metadata, and saved report export history.

Admin dashboard stack: separate Next.js repository using the FastAPI backend, protected admin auth, shared API client, dark SaaS admin UI, real backend data, browser Firebase Cloud Messaging token registration, and no fake telemetry.

Mobile app stack/status: Flutter mobile app in `ibrahimoll/planora-mobile`, currently focused on the user-facing auth UI flow using a clean light/dark purple Planora design system. Mobile auth screens are still UI-only; backend auth APIs are not connected yet.

Repositories:

- Backend: `ibrahimoll/planora-backend`
- Admin dashboard frontend: `ibrahimoll/planora-admin-dashboard`
- Mobile app: `ibrahimoll/planora-mobile`

## Current Verified Status

Latest confirmed status:

- Backend Step 31 Automatic Notification Scheduler is complete.
- Backend Step 32 Backend Total-Count Pagination is complete.
- Backend Step 33 Saved Report Export History is complete.
- Backend AI Chat Assistant now has a project-only scope guard: project/greeting questions are allowed, unrelated questions such as weather are blocked before the LLM provider is called.
- Gemini provider was configured locally through `.env` and verified manually by the user. The real `GEMINI_API_KEY` must stay local and must never be committed.
- Backend Alembic head is now `8b2c6d9f0a11`.
- Backend focused Step 33 test file `tests/test_22_report_export_history_api.py` passed with `3 passed`.
- Backend full regression passed after Step 33 with `139 passed`.
- Backend full regression passed after AI chat scope guard/Gemini verification with `140 passed`.
- Backend `python -m compileall app tests` passed after Step 33.
- Admin dashboard final polish pass is complete.
- Admin dashboard latest local verification after browser FCM work: `npm run lint` reported `0 errors`; `npm run build` passed.
- Browser FCM token registration was implemented and tested successfully on the web/laptop: browser permission prompt, real Firebase token registration, saved `web` device token, and test push notification received.
- Temporary admin-dashboard patch scripts were removed from the frontend repo.
- Mobile onboarding UI is complete in light/dark style and navigates to the login screen.
- Mobile login UI is complete and responsive, with light/dark mode toggle, Google logo, Apple placeholder button, Remember me, Forgot password link, and Sign up navigation.
- Mobile register UI is complete and responsive, with full name, email, password, confirm password, terms checkbox, Google/Apple buttons, and navigation to email verification.
- Mobile register password rules card is implemented. It appears when the password field is focused and updates live: empty password shows grey circles, failed rules show red X icons, and passed rules show green checks.
- Mobile email verification UI is complete and responsive. It has six OTP boxes, resend countdown, Verify Email button, Change Email button, and switches between `email_verification_light.png` and `email_verification_dark.png` based on theme.
- Mobile forgot password UI is the current next manual task. Desired flow: `ForgotPasswordScreen` -> `ResetLinkSentScreen`, with separate light/dark illustration assets for each state.
- Mobile backend connection is not started yet. Login, register, email verification, forgot password, resend, Google, and Apple actions should remain placeholders or local navigation until the auth UI flow is complete.

Important backend verification commands:

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

Important admin dashboard verification commands:

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\admin-dashboard
git pull origin main
npm run lint
npm run build
```

Important mobile verification commands:

```powershell
cd C:\Users\Ibrahim\Documents\Planora\mobile
git pull origin main
flutter pub get
flutter analyze
flutter run -d chrome
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

## Mobile App Current UI Direction

The mobile UI should follow the clean, modern, friendly, professional Planora light/dark purple identity:

- Primary purple gradient buttons.
- Rounded white/light cards in light mode.
- Dark navy surfaces in dark mode.
- Soft lavender/purple backgrounds and accents.
- Centered Planora logo and `AI-POWERED PROJECT PLANNING` pill on auth screens.
- Responsive layouts using `LayoutBuilder`, `SingleChildScrollView`, max content width, keyboard-safe scrolling, and `AuthResponsiveMetrics`.
- The auth screens should support small phones, normal phones, tablet/web widths, and keyboard-open states.

Current mobile files/features to remember:

- Shared auth responsive helper: `lib/features/auth/shared/auth_responsive_metrics.dart`.
- Login screen: `lib/features/login/login_screen.dart`.
- Register screen: `lib/features/register/register_screen.dart`.
- Email verification screen: `lib/features/email_verification/email_verification_screen.dart`.
- Planned forgot password screen path: `lib/features/forgot_password/forgot_password_screen.dart`.
- Google logo asset: `assets/icons/google_logo.svg`.
- Email verification assets:
  - `assets/images/email_verification_light.png`
  - `assets/images/email_verification_dark.png`
- Planned forgot password assets:
  - `assets/images/forgot_password_light.png`
  - `assets/images/forgot_password_dark.png`
  - `assets/images/reset_link_sent_light.png`
  - `assets/images/reset_link_sent_dark.png`

Mobile auth UI flow target before API integration:

1. Onboarding -> Login.
2. Login -> Register.
3. Register -> Email verification.
4. Login -> Forgot password.
5. Forgot password -> Reset link sent.
6. Later add Reset password screen if using code-based reset in-app instead of email link.
7. After UI flow is stable, connect backend APIs and secure token storage.

Important mobile/backend integration note:

- Backend auth already supports normal registration/login, email verification, resend verification code, forgot password, reset password, `/auth/me`, and Google login.
- Mobile UI currently does not call these APIs.
- Apple login should stay UI-only/coming-later unless Apple Developer setup is available.
- Backend register may still require `username`; the current mobile register UI does not show username. Before API integration, decide whether mobile should generate username from email/full name or backend should auto-generate username.

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
