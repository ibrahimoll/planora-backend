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

## Frontend Feature Backlog From Backend Comparison

These backend features exist but are missing or only partially integrated in the admin dashboard frontend. Use this list as the next work queue.

### High-priority admin-facing missing pages/features

1. Admin Logs page

- Suggested route: `/dashboard/admin-logs`
- Backend route: `GET /admin/logs`
- Needed UI: log table/list, filters for admin, target user, action, created_from, created_to, limit, offset.
- Purpose: audit admin actions such as role changes, activation/deactivation, project moderation, and task moderation.

2. Full Notifications page

- Suggested route: `/dashboard/notifications`
- Backend routes: `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{notification_id}/read`, `PATCH /notifications/read-all`, `DELETE /notifications/{notification_id}`.
- Current status: topbar notification dropdown exists only.
- Needed UI: full notification center, unread filter, type filter, mark one read, mark all read, delete notification, empty/loading/error states.

3. Admin Reports expansion

- Existing route: `/dashboard/reports`
- Admin backend routes: `GET /admin/reports/system-summary`, `GET /admin/reports/projects-summary`, `GET /admin/reports/users-summary`.
- Current status: page focuses mostly on project report generation using `/reports/projects/{project_id}`.
- Needed UI: admin system summary, projects summary, users summary, printable/exportable sections, and clear separation between system reports and single-project reports.

4. Push Notification management

- Suggested location: `/dashboard/settings` section or `/dashboard/push-notifications`.
- Backend routes: `GET /push-notifications/status`, `GET /push-notifications/preferences`, `PATCH /push-notifications/preferences`, `GET /push-notifications/device-tokens`, `PATCH /push-notifications/device-tokens/{device_token_id}/deactivate`, `POST /push-notifications/test`.
- Needed UI: Firebase configured/enabled status, push preference toggles, registered device tokens list, deactivate token action, send test push form.

5. Deadline Reminder admin scan panel

- Suggested location: dashboard overview utility panel, reports page, or settings/admin tools section.
- Backend routes: `POST /deadline-reminders/run`, `GET /deadline-reminders/me`.
- Needed UI: hours-ahead input, include-overdue toggle, run scan button, result summary, and reminder list/preview.

### Medium-priority project/admin integrations

6. Project Activity Timeline

- Suggested location: project detail panel/page.
- Backend route: `GET /projects/{project_id}/activity`.
- Current status: dashboard overview shows recent activity globally through `/admin/dashboard/recent-activity`, but individual project activity is not shown.
- Needed UI: timeline list with event type filter, limit/offset, actor, event message, and created_at.

7. AI Project Planning panel

- Suggested location: project detail page/panel.
- Backend routes: `POST /projects/{project_id}/ai-plans`, `GET /projects/{project_id}/ai-plans`, `POST /teams/{team_id}/projects/{project_id}/ai-plans`, `GET /teams/{team_id}/projects/{project_id}/ai-plans`.
- Needed UI: generate AI plan form, option to create tasks if backend request supports it, AI plan history, generated milestones/tasks display.
- Note: this may be better for user/mobile project workspace, but admin can inspect or trigger it if desired.

8. AI Chat Assistant panel

- Suggested location: project detail page or separate project workspace route.
- Backend routes: `POST /projects/{project_id}/chat`, `GET /projects/{project_id}/chat`, `POST /teams/{team_id}/projects/{project_id}/chat`, `GET /teams/{team_id}/projects/{project_id}/chat`.
- Needed UI: project-scoped chat history, message composer, assistant context summary.
- Note: this is more user-facing than admin-facing, but it is a major Planora AI feature.

9. Smart Scheduling panel

- Suggested location: project detail page/panel.
- Backend routes: `POST /projects/{project_id}/smart-schedules/preview`, `POST /projects/{project_id}/smart-schedules`, `GET /projects/{project_id}/smart-schedules`, plus team-project equivalents.
- Needed UI: preview schedule, apply schedule, show schedule history, visualize task due-date changes.
- Note: stronger fit for user/team project workspace but can be added to admin project oversight later.

### Lower-priority or user/mobile-oriented features

10. Invitations UI

- Backend routes: `POST /teams/{team_id}/invitations`, `GET /invitations/me`, `POST /invitations/{invitation_id}/accept`, `POST /invitations/{invitation_id}/reject`.
- Needed UI: pending invitations list, accept/reject buttons, invite user form inside team management.
- Note: likely belongs in user/mobile/team workspace more than admin dashboard.

11. Productivity Insights page

- Backend route: `GET /insights/me`.
- Needed UI: user productivity insight cards, workload status, project health, recommendations.
- Note: mostly user-facing, not admin-facing, unless admin impersonation or per-user insights are added later.

12. User-facing project/task/team CRUD pages

- Backend has full non-admin project, task, team, team-project, team-task, comments, attachments, progress, risk-analysis, and report APIs.
- Admin dashboard should not necessarily duplicate all user/mobile workflows.
- Keep admin dashboard focused on oversight, moderation, reporting, logs, system health, notifications, and settings.

## Recommended Next Build Order

1. `/dashboard/admin-logs`
2. `/dashboard/notifications`
3. Expand `/dashboard/reports` with admin summary reports
4. Push Notifications section in `/dashboard/settings`
5. Deadline Reminder scan panel
6. Project Activity Timeline inside `/dashboard/projects`
7. AI Plan / AI Chat / Smart Scheduling panels if admin demo needs AI visibility

## Current Next Step

Continue admin-dashboard polish and remaining Step 30 pages:

- Confirm auth pages visually after removing the marketing section.
- Run `npm run lint` and `npm run build` in `admin-dashboard`.
- Start next with `/dashboard/admin-logs`, then `/dashboard/notifications`.
