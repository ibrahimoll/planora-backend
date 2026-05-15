# Planora Backend Context

## Main Idea

Planora is an AI-powered project planning and collaboration system with:

- Mobile app for users/team members.
- Web admin dashboard for administrators.
- No guest access past authentication.
- Personal Project Mode.
- Team Collaboration Mode.
- AI planning, smart scheduling, risk prediction, productivity insights, and AI chat assistant planned for later phases.

The backend currently uses FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic v2, Google social login, SMTP email for verification/reset flows, and local file storage for development.

Firebase decision:

- Firebase Cloud Messaging will be used later for real mobile push notifications.
- Firebase Storage will be used later for attachments/files.
- For now, notifications are stored as in-app rows in the `notifications` table.
- For now, attachments are stored locally during backend development.

## Current Verified Status — 2026-05-15

Completed backend steps:

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

Important current notes:

- Google-created accounts cannot use Swagger password authorization unless they set a Planora password through forgot/reset password.
- Google-created users normally authenticate through `POST /auth/google` and receive a Planora JWT.
- `notifications.type` must allow: `task`, `project`, `team`, `comment`, `mention`, `invite`, `deadline`, `ai`, `risk`, `system`.
- If invitation or mention notifications fail when inserting notification type `invite` or `mention`, fix the live PostgreSQL notification check constraint.
- Team roles and project roles are separate.
- Updating `team_members.role` does not update `project_members.role`.
- A team `admin` is not automatically a project `manager`.

## Step 12 — Invitation System Completed

Step 12 uses the existing `invitations` table. Do not create a separate `team_invitations` table.

Current invitation flow:

- Team owner/admin invites by Planora username.
- Backend resolves `users.username` to `invited_user_id`.
- `email` stays `NULL` for current registered-user app flow.
- Backend creates a pending row in `invitations`.
- Backend creates an in-app notification with `type = invite`.
- Invited user can list pending invitations.
- Invited user can accept or reject.
- Accepting adds the user to `team_members`.
- Accepting also adds the user to existing team projects as project `member`, unless already present.

Expected/implemented Step 12 files:

- `app/models/invitation.py`
- `app/schemas/invitation_schema.py`
- `app/services/invitation_service.py`
- `app/routers/invitation_routes.py`
- `app/main.py` includes `invitation_router`

Step 12 endpoints:

- `POST /teams/{team_id}/invitations`
- `GET /invitations/me`
- `POST /invitations/{invitation_id}/accept`
- `POST /invitations/{invitation_id}/reject`

Current invitation table columns:

- `invitation_id`
- `invited_by`
- `invited_user_id`
- `email`
- `team_id`
- `project_id`
- `role`
- `status`
- `expires_at`
- `created_at`
- `responded_at`

Invitation status values:

- `pending`
- `accepted`
- `rejected`
- `expired`

Invitation role values:

- `admin`
- `manager`
- `member`

Team invitation role rule:

- Team invitations should only use `admin` or `member`.
- `manager` is for project-level invitations later.
- `owner` should not be assignable through normal invitations.

Duplicate invite rule:

- Prevent duplicate pending invitations for the same team and same invited user.

Recommended partial unique index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_invitations_pending_team_user
ON invitations(team_id, invited_user_id)
WHERE status = 'pending' AND project_id IS NULL;
```

Notification constraint fix if needed:

```sql
ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS fk_notifications_type;

ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS chk_notifications_type;

ALTER TABLE notifications
ADD CONSTRAINT chk_notifications_type
CHECK (
    type IN (
        'task',
        'project',
        'team',
        'comment',
        'mention',
        'invite',
        'deadline',
        'ai',
        'risk',
        'system'
    )
);
```

## Step 13 — Mentions in Comments Completed

Step 13 adds `@username` mentions inside task comments.

Current mention behavior:

- User writes a comment containing one or more usernames, for example `@ali`.
- Backend parses mentioned usernames from `comment_text`.
- Backend ignores duplicate usernames inside the same comment.
- Backend checks that the username exists and belongs to the same project before creating a mention.
- For team projects, only project members can be mentioned.
- For personal projects, the system should not notify random outside users.
- Backend saves mention rows in `comment_mentions`.
- Backend creates in-app notifications with `type = mention`.
- The author should not receive a mention notification for mentioning themselves.
- When a comment is updated, old mention rows are replaced based on the new comment text.
- When a comment is deleted, related mention rows are deleted through cascade.

Expected/implemented Step 13 files:

- `app/models/comment_mention.py`
- Updated `app/models/comment.py`
- Updated `app/models/user.py`
- Updated `app/models/__init__.py`
- Updated `app/services/comment_service.py`
- Updated `app/routers/comment_routes.py`

Current `comment_mentions` table columns:

- `mention_id`
- `comment_id`
- `project_id`
- `task_id`
- `mentioned_user_id`
- `mentioned_by`
- `created_at`

Important constraints/indexes:

- `comment_id` references `comments(comment_id)` with `ON DELETE CASCADE`.
- `project_id` references `projects(project_id)` with `ON DELETE CASCADE`.
- `task_id` references `tasks(task_id)` with `ON DELETE CASCADE`.
- `mentioned_user_id` references `users(user_id)` with `ON DELETE CASCADE`.
- `mentioned_by` references `users(user_id)` with `ON DELETE CASCADE`.
- Unique rule: one mentioned user should appear only once per comment.
- Indexes should exist for `comment_id`, `project_id`, `task_id`, `mentioned_user_id`, and `mentioned_by`.

Recommended SQL for existing databases:

```sql
CREATE TABLE IF NOT EXISTS comment_mentions (
    mention_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    comment_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    task_id BIGINT NOT NULL,
    mentioned_user_id BIGINT NOT NULL,
    mentioned_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comment_mentions_comment
        FOREIGN KEY (comment_id)
        REFERENCES comments(comment_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_project
        FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_task
        FOREIGN KEY (task_id)
        REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_mentioned_user
        FOREIGN KEY (mentioned_user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_mentions_mentioned_by
        FOREIGN KEY (mentioned_by)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_comment_mentions_comment_user
        UNIQUE (comment_id, mentioned_user_id)
);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_comment
ON comment_mentions(comment_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_project
ON comment_mentions(project_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_task
ON comment_mentions(task_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_mentioned_user
ON comment_mentions(mentioned_user_id);

CREATE INDEX IF NOT EXISTS idx_comment_mentions_mentioned_by
ON comment_mentions(mentioned_by);
```

Step 13 manual test expectation:

- Create or update a team task comment containing `@username`.
- The mentioned user must be a project member.
- The mentioned user should see an unread notification from `GET /notifications?unread_only=true`.
- The notification should have `type = mention`.

## Role Management Decision

There are two separate membership systems:

- `team_members.role`: `owner`, `admin`, `member`.
- `project_members.role`: `owner`, `manager`, `member`.

Team role endpoint:

- `PATCH /teams/{team_id}/members/{user_id}` updates `team_members.role`.
- Only the team owner should be allowed to update team member roles.
- Team member role update should only allow `admin` and `member`.
- Do not allow assigning `owner` through normal role update.
- Ownership transfer should be a separate future feature if needed.

Project role endpoint still needed:

- Add `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}`.
- This should update `project_members.role`.
- It should allow changing between `manager` and `member`.
- It should not allow assigning `owner` through normal role update.

Important behavior:

- If user 2 is changed to team `admin`, `GET /teams/{team_id}/members` should show admin.
- `GET /teams/{team_id}/projects/{project_id}/members` can still show project `member` because that reads `project_members.role`.
- This is expected, not a bug.

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
- `ai_plans`
- `risk_analysis`
- `user_progress`
- `chat_messages`
- `admin_logs`
- `email_verification_codes`
- `password_reset_codes`
- `oauth_accounts`

Planned/polish tables:

- `activity_logs`
- `device_tokens` for Firebase Cloud Messaging tokens
- `notification_preferences`
- Optional reminder-tracking table for deadline reminders
- Optional report export history table

## Roadmap From Here

Immediate cleanup:

- Add project-member role update endpoint.
- Fix `TeamMemberUpdate` so normal team role update accepts only `admin` or `member`, not `owner`.
- Add tests for invitations, mentions, and role-update permissions.

Next feature step:

- Step 14 — Deadline reminders.

Later steps:

- Progress tracking and productivity insights.
- Activity timeline.
- AI project planning and smart scheduling.
- Risk analysis.
- AI chat assistant.
- Export project report.
- Admin dashboard APIs.
- CORS/frontend/mobile integration.
- Firebase FCM for push notifications.
- Firebase Storage for attachments.
- Tests/security cleanup/Alembic.
- Docker and deployment polish.

## User Preference

- Do not provide long PowerShell test scripts by default.
- Prefer Swagger, Thunder Client, or short manual API testing instructions unless PowerShell is explicitly requested.
