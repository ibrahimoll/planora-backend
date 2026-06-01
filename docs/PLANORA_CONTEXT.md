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

Mobile app stack/status: Flutter mobile app in `ibrahimoll/planora-mobile`, currently moving from completed auth UI screens into backend API integration. Mobile auth screens are still mostly UI/local-navigation only; backend auth APIs are the active next implementation target.

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
- Deployment milestone: user has deployed the backend, PostgreSQL database, and web/admin dashboard site. Mobile development is now the active next phase.
- Admin dashboard final polish pass is complete.
- Admin dashboard latest local verification after browser FCM work: `npm run lint` reported `0 errors`; `npm run build` passed.
- Browser FCM token registration was implemented and tested successfully on the web/laptop: browser permission prompt, real Firebase token registration, saved `web` device token, and test push notification received.
- Temporary admin-dashboard patch scripts were removed from the frontend repo.
- Mobile onboarding UI is complete in light/dark style and navigates to login/register.
- Mobile login UI is complete and responsive, with light/dark mode toggle, Google logo, Apple placeholder button, Remember me, Forgot password link, and Sign up navigation.
- Mobile register UI is complete and responsive, with full name, email, password, confirm password, terms checkbox, Google/Apple buttons, and navigation to email verification.
- Mobile register password rules card is implemented. It appears when the password field is focused and updates live: empty password shows grey circles, failed rules show red X icons, and passed rules show green checks.
- Mobile email verification UI is complete and responsive. It has six OTP boxes, resend countdown, Verify Email button, Change Email button, and switches between `email_verification_light.png` and `email_verification_dark.png` based on theme.
- Mobile forgot password UI is complete. Current flow: `ForgotPasswordScreen` -> `ResetLinkSentScreen`, using separate light/dark assets:
  - `assets/images/forgot_password_light.png`
  - `assets/images/forgot_password_dark.png`
  - `assets/images/reset_link_sent_light.png`
  - `assets/images/reset_link_sent_dark.png`
- Mobile backend connection is now the active next task. Login, register, email verification, forgot password, resend, Google, and Apple actions are still placeholders/local navigation until API integration is completed.
- Mobile API foundation has been started/planned with:
  - `lib/core/config/app_config.dart`
  - `lib/core/network/api_client.dart`
  - `lib/core/network/api_exception.dart`
  - `lib/core/storage/token_storage.dart`
- `token_storage.dart` should use `const FlutterSecureStorage()` directly. Do not use deprecated `AndroidOptions(encryptedSharedPreferences: true)` because `encryptedSharedPreferences` is deprecated and ignored by newer `flutter_secure_storage` versions.
- Future coding guidance requested by the user: explain each step in English first, then provide code function-by-function with explanation. Avoid dumping a large file before explaining the purpose of each function.

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

Run mobile against deployed backend with:

```powershell
flutter run -d chrome --dart-define=PLANORA_API_URL=https://YOUR_BACKEND_URL
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
- Forgot password screen: `lib/features/forgot_password/forgot_password_screen.dart`.
- Reset link sent screen currently lives inside `lib/features/forgot_password/forgot_password_screen.dart` as `ResetLinkSentScreen`.
- Google logo asset: `assets/icons/google_logo.svg`.
- Email verification assets:
  - `assets/images/email_verification_light.png`
  - `assets/images/email_verification_dark.png`
- Forgot password assets:
  - `assets/images/forgot_password_light.png`
  - `assets/images/forgot_password_dark.png`
  - `assets/images/reset_link_sent_light.png`
  - `assets/images/reset_link_sent_dark.png`

Mobile auth UI flow status:

1. Onboarding -> Login/Register is implemented.
2. Login -> Register is implemented.
3. Register -> Email verification is implemented locally.
4. Login -> Forgot password is implemented.
5. Forgot password -> Reset link sent is implemented locally.
6. Backend reset password is code-based, so a real in-app `ResetPasswordScreen` is still needed if the app should complete password reset from the mobile UI.
7. After API integration, successful login should save the JWT access token and route into the app instead of staying in auth placeholders.

Mobile backend integration plan:

1. Finish/check API foundation files:
   - `AppConfig` reads `PLANORA_API_URL` from `--dart-define` and trims trailing `/`.
   - `ApiException` stores clean backend error messages and optional status codes.
   - `TokenStorage` saves, reads, clears, and checks JWT access token using `flutter_secure_storage`.
   - `ApiClient` wraps Dio and provides `get`, `postJson`, `postForm`, `patchJson`, and `delete` helpers.
2. Add auth models and auth API layer:
   - `lib/features/auth/models/auth_models.dart`
   - `lib/features/auth/data/auth_api.dart`
   - Models/functions: `TokenResponse`, `UserResponse`, `MessageResponse`, `login`, `register`, `verifyEmail`, `resendVerificationCode`, `forgotPassword`, `resetPassword`, `getCurrentUser`.
3. Connect login screen:
   - Validate email/password.
   - Show loading state.
   - Call `POST /auth/login` using form data with fields `username` and `password`.
   - Save `access_token`.
   - Call `/auth/me`.
   - Route to a temporary home screen.
4. Connect register screen:
   - Validate full name/email/password.
   - Backend requires `username`, `email`, `password`, and `full_name`.
   - Current mobile UI has no username field, so use generated username from email for now unless backend is changed to auto-generate username.
   - Call `POST /auth/register`.
   - Route to email verification screen after successful registration.
5. Connect email verification screen:
   - Call `POST /auth/verify-email`.
   - Call `POST /auth/resend-verification-code`.
   - After verification, route user to login or auto-login only if a token flow is added later.
6. Connect forgot/reset password:
   - `ForgotPasswordScreen` should call `POST /auth/forgot-password`.
   - Add `ResetPasswordScreen` for backend's code-based reset flow.
   - `ResetPasswordScreen` should collect email, 6-digit code, new password, and confirm password, then call `POST /auth/reset-password`.
7. Add `AuthGate`:
   - If token exists and `/auth/me` works, route to Home.
   - Otherwise route to Onboarding/Login.
8. Add temporary Home screen:
   - Show basic authenticated state.
   - Add logout button that clears token.
   - Later replace with the real mobile dashboard.

Important mobile/backend integration note:

- Backend auth already supports normal registration/login, email verification, resend verification code, forgot password, reset password, `/auth/me`, and Google login.
- Mobile UI currently does not call these APIs.
- Apple login should stay UI-only/coming-later unless Apple Developer setup is available.
- Google login should be implemented after normal email/password auth unless specifically prioritized.
- Backend register requires `username`; the current mobile register UI does not show username. For the first mobile API integration, generate a username from email locally or update backend to auto-generate username.

Preferred mobile coding workflow:

- Explain the purpose of the current step in English first.
- Then provide code one function/class at a time.
- For each function/class, explain:
  1. Function/class name.
  2. What it does.
  3. Why Planora needs it.
  4. The exact code for that function/class.
  5. What to test before continuing.
- Avoid giving huge multi-file code dumps unless explicitly requested.

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
