# Planora Admin Dashboard Update — 2026-05-18

This addendum records the latest admin-dashboard frontend state after the responsive layout/auth UI polish work.

## Repository

- Admin dashboard frontend: `ibrahimoll/planora-admin-dashboard`
- Backend context file: `docs/PLANORA_CONTEXT.md` in `ibrahimoll/planora-backend`

## Latest Confirmed Admin Dashboard State

- Dashboard layout uses the dark Planora SaaS/admin style.
- Sidebar and topbar are aligned using matching `104px` header height.
- Sidebar remains visible while scrolling by using sticky/full-height behavior.
- Topbar remains visible while dashboard content scrolls.
- Topbar includes a burger/sidebar toggle, dashboard search, notification dropdown, verified admin badge, profile dropdown, and logout button.
- The verified admin badge uses a green live dot/pulse indicator.
- Dashboard search navigates between dashboard sections such as Overview, Users, Projects, Tasks, Risk, Reports, and Settings.
- Notification dropdown closes on outside click and Escape.
- Notifications load from the real backend route `GET /notifications`.
- Mark all read uses the real backend route `PATCH /notifications/read-all`, so read state persists after refresh.
- Notification unread badge is based on `is_read === false`.
- Profile menu uses `adminProfileSync` helpers and falls back to initials if the profile image is missing or broken.
- Topbar profile text styling was softened by removing heavy/bold styling.
- Logout uses `clearAdminToken()` so it clears the real `planora_admin_token` key.

## Auth Pages

Shared auth layout:

- `components/auth/AdminAuthShell.tsx`

Current auth page direction:

- Keep only a centered auth card.
- Remove the large left-side marketing/feature section.
- Use the real `PlanoraLogo` so login, forgot password, and reset password match the dashboard/sidebar branding.
- Keep the same dark Planora theme as the dashboard.

Auth routes:

- `/login`
- `/forgot-password`
- `/reset-password`

Login page:

- Uses `POST /auth/login`.
- Saves the JWT using `saveAdminToken()` under `planora_admin_token`.
- Calls `/auth/me` and requires `role = admin`.
- Saves admin profile using `saveAdminProfile()` after successful `/auth/me`.
- Blocks non-admin accounts and clears token.

Forgot password page:

- Uses `POST /auth/forgot-password`.
- Sends reset code to admin email.
- Redirects to `/reset-password?email=...` after request.
- Matches the simplified centered auth card style.

Reset password page:

- Uses `POST /auth/reset-password`.
- Prefills email from the `email` query parameter when present.
- Supports 6-digit reset code, new password, confirm password, show/hide password buttons, and frontend validation matching backend password rules.
- Includes an inline Resend code button that calls `POST /auth/forgot-password` without leaving the page.
- Redirects to `/login` after successful reset.

## Important Token Rule

Use only the auth helpers from `lib/auth.ts`:

- `saveAdminToken()`
- `getAdminToken()`
- `clearAdminToken()`

Do not manually check or clear stale keys like `access_token`, `token`, or `admin_token` in the admin dashboard frontend. The real admin token key is `planora_admin_token`.

## Files Updated/Relevant

Admin dashboard frontend files:

- `components/layout/AdminSidebar.tsx`
- `components/layout/AdminTopbar.tsx`
- `components/layout/ProtectedAdminLayout.tsx`
- `components/auth/AdminAuthShell.tsx`
- `app/login/page.tsx`
- `app/forgot-password/page.tsx`
- `app/reset-password/page.tsx`
- `app/globals.css`
- `lib/auth.ts`
- `lib/adminProfileSync.ts`
- `lib/api.ts`

Backend routes used:

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /notifications`
- `PATCH /notifications/read-all`

## Current Next Step

Continue admin-dashboard polish and remaining Step 30 pages:

- Confirm auth pages visually after removing the marketing section.
- Run `npm run lint` and `npm run build` in `admin-dashboard`.
- Continue with Admin Tasks Page, Risk Center Page, Reports Page, Activity/Notifications page, and Admin Settings page.
