# Step 34 — Browser QA With Seeded Data

Status: started.

## Goal

Use realistic local demo data to verify Planora in the browser before demo/presentation.

```text
Seed realistic Planora data
→ open backend + admin dashboard
→ verify dashboard pages with real API responses
→ record pass/fail notes
→ fix UI/API issues before moving to mobile/user frontend work
```

## Repositories

- Backend: `ibrahimoll/planora-backend`
- Admin dashboard: `ibrahimoll/planora-admin-dashboard`

## Backend preparation

Run from the backend folder:

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\backend
git pull origin main
alembic upgrade head
alembic current
python -m compileall app tests
```

Expected Alembic head after Step 33:

```text
8b2c6d9f0a11
```

## Backend verification before browser QA

```powershell
$pgPassword = Read-Host "Enter your PostgreSQL postgres password"
$encodedPassword = [uri]::EscapeDataString($pgPassword)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/planora_test_db"
python -m pytest -x -v
python -m pytest -v
```

Latest verified result before Step 34:

```text
139 passed
```

## Admin dashboard preparation

Run from the admin dashboard folder:

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\admin-dashboard
git pull origin main
npm run lint
npm run build
npm run dev
```

## Backend local server

Run from the backend folder:

```powershell
uvicorn app.main:app --reload
```

Expected backend URL:

```text
http://localhost:8000
```

Expected admin dashboard URL:

```text
http://localhost:3000
```

## Demo login accounts

Use the accounts created by the seed process.

Recommended local demo accounts:

```text
Admin:   demo.admin@planora.local
Owner:   demo.owner@planora.local
Manager: demo.manager@planora.local
Member:  demo.member@planora.local
```

Use a local-only password stored in your environment. Do not commit real passwords or secrets.

## Page-by-page QA checklist

### Login

- [ ] Admin can log in through the normal login page.
- [ ] Non-admin user cannot access admin dashboard routes.
- [ ] Invalid login shows a clear error.
- [ ] Refresh keeps the admin session if the token is valid.

### Dashboard overview — `/dashboard`

- [ ] Overview cards load real backend numbers.
- [ ] Recent activity loads real activity rows.
- [ ] No fake telemetry appears.
- [ ] Loading and empty states look correct.

### Users — `/dashboard/users`

- [ ] User list loads from `GET /admin/users`.
- [ ] Page reads `items`, `total`, `limit`, and `offset` from paginated backend response.
- [ ] Search works.
- [ ] Role filter works.
- [ ] Active/inactive filter works.
- [ ] Verified/unverified filter works.
- [ ] Pagination next/previous works using `total`.
- [ ] User detail panel loads.
- [ ] User activity load-more works.
- [ ] Activate/deactivate action works.
- [ ] Promote/demote action works.
- [ ] Admin cannot demote/deactivate self.

### Projects — `/dashboard/projects`

- [ ] Project list loads from `GET /admin/projects`.
- [ ] Page reads `items`, `total`, `limit`, and `offset` from paginated backend response.
- [ ] Search works.
- [ ] Status filter works.
- [ ] Project type filter works.
- [ ] Team filter works if available.
- [ ] Pagination next/previous works using `total`.
- [ ] Project detail panel loads.
- [ ] Personal project shows no team.
- [ ] Team project shows team data.
- [ ] Task stats display correctly.
- [ ] Latest risk displays correctly when available.
- [ ] Status update works and creates an admin log.

### Tasks — `/dashboard/tasks`

- [ ] Task list loads from `GET /admin/tasks`.
- [ ] Page reads `items`, `total`, `limit`, and `offset` from paginated backend response.
- [ ] Search works.
- [ ] Status filter works.
- [ ] Priority filter works.
- [ ] Project filter works if available.
- [ ] Assignee filter works if available.
- [ ] Pagination next/previous works using `total`.
- [ ] Task detail panel loads.
- [ ] Status update works.
- [ ] Assignment update works.
- [ ] Unassignment works if supported in UI.

### Risk — `/dashboard/risk`

- [ ] Risk summary loads.
- [ ] High-risk projects list loads.
- [ ] High-risk seeded project is visible.
- [ ] Risk level labels are clear.
- [ ] Recommendations are readable.
- [ ] Empty state works if filters return no results.

### Reports — `/dashboard/reports`

- [ ] System Summary tab loads.
- [ ] Projects Summary tab loads.
- [ ] Users Summary tab loads.
- [ ] Project Report tab loads.
- [ ] Project report export works through `GET /reports/projects/{project_id}`.
- [ ] Export response includes `export_id`.
- [ ] Saved report export history can be checked through `GET /reports/exports`.
- [ ] Saved project report export history can be checked through `GET /reports/projects/{project_id}/exports`.

### Notifications — `/dashboard/notifications`

- [ ] Notification list loads.
- [ ] Unread count loads.
- [ ] Search/filter works.
- [ ] Mark one as read works.
- [ ] Mark all read works.
- [ ] Read state remains after refresh.
- [ ] Delete notification works.
- [ ] Empty state looks correct.

### Admin logs — `/dashboard/admin-logs`

- [ ] Admin logs load from `GET /admin/logs`.
- [ ] Page reads `items`, `total`, `limit`, and `offset` from paginated backend response.
- [ ] Action filter works.
- [ ] Target user filter works if available.
- [ ] Pagination next/previous works using `total`.
- [ ] New admin actions appear after status/role changes.

### Settings — `/dashboard/settings`

- [ ] Profile section loads.
- [ ] Profile picture displays correctly.
- [ ] Password change form works.
- [ ] Push notification status loads.
- [ ] Notification preferences load and save.
- [ ] Saved device tokens load.
- [ ] Browser FCM registration button works on localhost.
- [ ] Test push works if Firebase service account is configured.
- [ ] Token deactivation works.

## API checks for Step 33 report export history

Use Swagger, Thunder Client, or browser devtools.

```text
GET /reports/projects/{project_id}
GET /reports/exports
GET /reports/projects/{project_id}/exports
```

Expected export history response shape:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

## Pass criteria

Step 34 is considered complete when:

- [ ] Backend starts with Alembic at `8b2c6d9f0a11` or newer.
- [ ] Backend regression still passes.
- [ ] Admin dashboard lint passes.
- [ ] Admin dashboard build passes.
- [ ] All main dashboard pages load in browser.
- [ ] Step 32 pagination works in UI.
- [ ] Step 33 report export history works by API.
- [ ] Any UI bugs found during QA are either fixed or written down as known TODOs.

## Notes / bugs found

Write findings here while testing:

```text
- [ ] TODO:
```
