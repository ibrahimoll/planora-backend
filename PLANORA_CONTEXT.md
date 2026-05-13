# Planora Project Context

Last updated: 2026-05-13

## 1. Project Overview

Planora is an AI-powered project planning and collaboration system.

It includes:
- Mobile app for users/team members
- Web-based admin dashboard for administrators
- Backend API using FastAPI + SQLAlchemy + PostgreSQL
- No guest access past authentication

Main purpose:
Planora helps users and teams create projects, generate plans, manage tasks, collaborate, track progress, and receive AI-based productivity/risk suggestions.

## 2. Core Modes

### Personal Project Mode

Users can:
- Register/login
- Verify email
- Create personal projects
- Add tasks
- Update task status
- Track project/task progress
- Receive notifications later
- Use AI planning/chat later

### Team Collaboration Mode

Users can:
- Create teams
- Add/remove team members
- Create team projects
- Assign tasks to project members
- Manage team tasks
- Upload attachments later
- Add comments later
- Track team progress later
- Use AI workload/risk features later

## 3. Core AI Features Planned

Planned AI features:
- AI project planning
- AI-generated task breakdown
- Smart scheduling
- AI chat assistant
- Risk/delay prediction
- Productivity insights
- Workload balancing for teams

These are not fully implemented yet.

## 4. Backend Stack

Current backend stack:
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT authentication
- Argon2/password hashing through pwdlib
- Google login using google-auth
- SMTP email verification/reset flow

Project structure convention:
- `app/routes/` for route files
- `app/models/` for SQLAlchemy models
- `app/schemas/` for Pydantic schemas
- `app/services/` for business logic
- `app/dependencies/` for auth/current-user dependencies
- `app/core/` for config/security
- `app/db/` for database session
- `docs/` for project documentation/context

## 5. Authentication State

Authentication is essentially complete.

Implemented routes:
- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/resend-verification-code`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /auth/login`
- `POST /auth/google`
- `GET /auth/me`

Rules:
- Protected routes require active + email-verified user.
- No guest can get past authentication.
- Google login returns a Planora JWT.
- `/auth/me` requires a Planora JWT, not a Google ID token.
- Google-only users get a random unusable password hash.
- Apple login was removed/paused because Apple Developer setup is paid.

Important auth tables:
- `users`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

OAuth rule:
- `oauth_accounts.provider` should only allow `google`.

## 6. Current Database Design

Current intended Planora database has 17 tables:

1. `users`
2. `teams`
3. `team_members`
4. `projects`
5. `project_members`
6. `tasks`
7. `attachments`
8. `comments`
9. `notifications`
10. `ai_plans`
11. `risk_analysis`
12. `user_progress`
13. `chat_messages`
14. `admin_logs`
15. `email_verification_codes`
16. `password_reset_codes`
17. `oauth_accounts`

## 7. Important Database Rules

### users

Columns:
- `user_id`
- `username`
- `email`
- `password_hash`
- `full_name`
- `role`
- `is_active`
- `is_email_verified`
- `profile_pic`
- `created_at`

Allowed roles:
- `user`
- `admin`

### teams

Important columns:
- `team_id`
- `name`
- `created_by`
- `created_at`

`created_by` references `users(user_id)`.

### team_members

Links users to teams.

Roles:
- `owner`
- `admin`
- `member`

Important rule:
- A user should be unique per team using `UNIQUE(team_id, user_id)`.

### projects

Important columns:
- `project_id`
- `created_by`
- `team_id`
- `title`
- `description`
- `deadline`
- `status`
- `project_type`
- `created_at`
- `updated_at`

Project statuses:
- `not_started`
- `in_progress`
- `on_hold`
- `cancelled`
- `completed`

Project types:
- `personal`
- `team`

Important project rule:
- Personal projects require `team_id IS NULL`.
- Team projects require `team_id IS NOT NULL`.

### project_members

Links users to projects.

Roles:
- `owner`
- `manager`
- `member`

Important rule:
- A user should be unique per project using `UNIQUE(project_id, user_id)`.

### tasks

Important columns:
- `task_id`
- `project_id`
- `assigned_to`
- `created_by`
- `title`
- `description`
- `priority`
- `estimated_hours`
- `actual_hours`
- `status`
- `due_date`
- `completed_at`
- `created_at`

Task priorities:
- `low`
- `medium`
- `high`

Task statuses:
- `todo`
- `in_progress`
- `completed`
- `blocked`

Important task rules:
- Hours should be non-negative.
- Completed tasks require `completed_at IS NOT NULL`.
- Non-completed tasks require `completed_at IS NULL`.
- `assigned_to` may be nullable.
- `created_by` should usually be protected with `ON DELETE RESTRICT`.

### attachments

Attachments can link to:
- A project
- Optionally a task

Important intended rule:
- If an attachment belongs to a task, the task must belong to the same project.

### chat_messages

Sender types:
- `user`
- `ai`

Important rule:
- User messages require `sender_id`.
- AI messages require `sender_id IS NULL`.

## 8. Important SQL Fixes Already Identified

Because the tables already exist in PostgreSQL, editing the old `CREATE TABLE` SQL file does not change the live database.

Existing schema mistakes must be fixed using `ALTER TABLE`.

Important fixes:
1. `chk_tasks_priority` must check:
   `priority IN ('low', 'medium', 'high')`
   not `status` or `prio`.

2. `chk_oauth_accounts_provider` must check:
   `provider = 'google'`
   or:
   `provider IN ('google')`

3. `password_reset_codes` should have:
   `CHECK (expires_at > created_at)`

When checking constraints, use:
```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname IN (
    'chk_tasks_priority',
    'chk_oauth_accounts_provider',
    'chk_password_reset_codes_expiry'
);