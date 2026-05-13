# Planora Backend Context

## Purpose

Planora is an AI-powered project planning and collaboration backend. The current backend focuses on authentication, verified user access, personal projects, teams, team projects, and task assignment. AI planning, attachments, comments, notifications, progress analytics, chat, and admin tooling are planned but not implemented yet.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic v2
- JWT bearer authentication
- SMTP email delivery
- Google ID token login

## Current Features

- Register with email verification.
- Log in with username/email and password.
- Resend verification codes.
- Forgot/reset password with one-time reset codes.
- Google login for verified Google accounts.
- Protected routes require an active, email-verified user.
- Personal projects and personal tasks.
- Teams with owner, admin, and member roles.
- Team projects with owner, manager, and member project roles.
- Team task creation, assignment, status updates, and deletion.

## Important Security Rules

- Do not commit or expose `.env` values.
- Keep configuration in `app/core/config.py`.
- Keep protected routes behind `get_current_active_verified_user`.
- Do not add guest access beyond authentication.
- Google login should read the profile image from the Google `picture` claim.
- Adding a team member supports only `admin` and `member`; `owner` is not assignable through the add-member request.
- Team member removal must also remove that user's project memberships for all projects in the team.

## Authorization Model

- Team owners can delete teams and update member roles.
- Team owners and admins can manage team details and members.
- Team members can view teams they belong to.
- Team project access is based on `ProjectMember` records.
- Project owners and managers can create, update, assign, and delete team project tasks.
- Assigned project members can update only their own task status and actual hours.

## Database Notes

- `database/database_schema.sql` is a reference file and may not represent the live PostgreSQL database if ALTER TABLE migrations were already applied.
- The ORM models are the current backend source of truth for application behavior.
- A future Alembic migration setup should replace manual schema drift management.

## Known Deferred Work

- Add rate limiting and cooldowns for login, verification, resend verification, forgot password, and reset password flows.
- Add CORS configuration before frontend or admin dashboard integration.
- Add tests for auth, email rollback behavior, team/project authorization, project membership synchronization, and task permissions.
- Reconcile `database_schema.sql` with the ORM and live database migrations.
- Add structured logging around auth failures, email failures, and permission denials.
- Implement the Planora AI/collaboration roadmap: AI plans, attachments, comments, notifications, progress, chat, and admin dashboard.

## Local Backend Commands

```powershell
cd C:\Users\mahdi\OneDrive\Documents\Planora\backend
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\uvicorn.exe app.main:app --reload
```
