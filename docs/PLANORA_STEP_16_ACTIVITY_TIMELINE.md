# Planora Step 16 — Activity Timeline Memo

Date: 2026-05-15

## Status

Step 16 adds the Activity Timeline feature to Planora.

Current status:

- Activity timeline implementation is in place.
- Step 16 pytest coverage was expanded to cover realistic branches, not only the happy path.
- The user reported the latest FastAPI/SonarLint fix worked.
- Full backend regression should still be run with `python -m pytest -x -v` after pulling the latest patches.

## Feature Summary

The Activity Timeline records important project activity in a new `activity_logs` table.

Main endpoint:

```text
GET /projects/{project_id}/activity
```

The endpoint returns activity rows for a project, ordered newest first.

It supports:

- Optional filtering by `event_type`.
- `limit` pagination.
- `offset` pagination.
- Personal project access control.
- Team project member access control.

## New Table

New table:

```text
activity_logs
```

Columns:

- `activity_id`
- `project_id`
- `task_id`
- `actor_id`
- `event_type`
- `actor_username_snapshot`
- `actor_full_name_snapshot`
- `task_title_snapshot`
- `message`
- `metadata`
- `created_at`

Event types:

- `project_created`
- `project_updated`
- `task_created`
- `task_updated`
- `task_completed`
- `task_deleted`
- `comment_created`
- `comment_updated`
- `comment_deleted`
- `attachment_uploaded`
- `attachment_deleted`
- `deadline_reminder_generated`

## Files Added

- `app/models/activity_log.py`
- `app/schemas/activity_log_schema.py`
- `app/services/activity_log_service.py`
- `app/routers/activity_log_routes.py`
- `tests/test_activity_log_routes.py`

## Files Updated

- `app/models/__init__.py`
- `app/models/project.py`
- `app/models/user.py`
- `app/models/task.py`
- `app/main.py`
- `app/services/project_service.py`
- `app/services/task_service.py`
- `app/services/comment_service.py`
- `app/routers/comment_routes.py`
- `app/services/attachment_service.py`
- `app/routers/attachment_routes.py`

## Current Behavior

Personal projects:

- Project owner can list activity.
- Other users cannot list private personal project activity.
- Unauthorized/private access returns `404 Project not found` where appropriate to avoid leaking project existence.

Team projects:

- Team project members can list project activity.
- Non-members cannot list team project activity.

Authentication:

- Missing token returns `401 Unauthorized`.

Filtering and pagination:

- `event_type` filter works.
- Invalid `event_type` returns `422`.
- `limit` must be between 1 and 100.
- `offset` must be 0 or higher.
- Invalid `limit` or `offset` returns `422`.

Ordering:

- Activity logs are returned newest first.

Snapshots:

- Activity logs keep actor/task snapshot fields so timeline text stays useful later.

## Test Coverage

The Step 16 test file is:

```text
tests/test_activity_log_routes.py
```

Coverage includes:

- `project_created` log.
- `project_updated` log.
- `task_created` log.
- `task_updated` log.
- `task_completed` log.
- `task_deleted` log and snapshot preservation.
- `comment_created` log.
- `comment_updated` log.
- `comment_deleted` log.
- `attachment_uploaded` log.
- `attachment_deleted` log.
- Newest-first ordering.
- Filtering by `event_type`.
- Invalid `event_type` returns `422`.
- `limit` and `offset` pagination.
- Invalid `limit` and `offset` return `422`.
- Project activity isolation.
- Empty activity list behavior.
- Other user cannot access personal project activity.
- Team project member can access team project activity.
- Team project non-member cannot access team project activity.
- Missing token returns `401`.

Run Step 16 tests:

```powershell
python -m pytest tests/test_activity_log_routes.py -v
```

Run full regression:

```powershell
python -m pytest -x -v
```

## Bugs Fixed During Step 16

1. Wrong model import path:

Bad:

```python
from backend.app.models.activity_log import ActivityLog
```

Fixed:

```python
from app.models.activity_log import ActivityLog
```

2. Missing `Task.activity_logs` relationship caused SQLAlchemy mapper startup failure.

Fixed by adding:

```python
activity_logs: Mapped[list["ActivityLog"]] = relationship(
    back_populates="task",
)
```

3. Git merge conflict markers were accidentally present in `app/models/task.py`.

Removed markers like:

```text
<<<<<<< Updated upstream
=======
>>>>>>> Stashed changes
```

4. Step 16 tests showed comment actions were not logged.

Fixed by updating:

- `app/services/comment_service.py`
- `app/routers/comment_routes.py`

5. Step 16 tests showed attachment actions were not logged.

Fixed by updating:

- `app/services/attachment_service.py`
- `app/routers/attachment_routes.py`

6. SonarLint `python:S8410` in `activity_log_routes.py`.

Fixed by using `Annotated` query aliases.

7. FastAPI startup error from putting defaults inside `Query()` in an `Annotated` alias.

Correct pattern:

```python
ActivityEventTypeQuery = Annotated[ActivityLogEventType | None, Query()]
ActivityLimitQuery = Annotated[int, Query(ge=1, le=100)]
ActivityOffsetQuery = Annotated[int, Query(ge=0)]

# defaults go here
event_type: ActivityEventTypeQuery = None
limit: ActivityLimitQuery = 50
offset: ActivityOffsetQuery = 0
```

8. SonarLint `python:S3776` cognitive complexity in `task_service.py`.

Fixed by refactoring task update logic into helper functions:

- `apply_task_field_update`
- `apply_task_updates`
- `get_task_update_activity_event_type`
- `log_task_update_activity`
- `update_task`

## Existing Database SQL Reminder

Because Planora tables already exist in PostgreSQL, editing SQLAlchemy models does not automatically update the live development database.

For the real local/dev database, create `activity_logs` manually or through migration.

Recommended SQL:

```sql
CREATE TABLE IF NOT EXISTS activity_logs (
    activity_id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id BIGINT NULL REFERENCES tasks(task_id) ON DELETE SET NULL,
    actor_id BIGINT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    actor_username_snapshot VARCHAR(50) NULL,
    actor_full_name_snapshot VARCHAR(150) NULL,
    task_title_snapshot VARCHAR(200) NULL,
    message TEXT NOT NULL,
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_activity_logs_event_type CHECK (
        event_type IN (
            'project_created',
            'project_updated',
            'task_created',
            'task_updated',
            'task_completed',
            'task_deleted',
            'comment_created',
            'comment_updated',
            'comment_deleted',
            'attachment_uploaded',
            'attachment_deleted',
            'deadline_reminder_generated'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_project_created_at
ON activity_logs(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_actor_created_at
ON activity_logs(actor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_task_id
ON activity_logs(task_id);

CREATE INDEX IF NOT EXISTS idx_activity_logs_event_type
ON activity_logs(event_type);
```

## Testing Rule Going Forward

For each backend step, test every realistic branch:

- Success path.
- Missing token.
- Wrong user.
- Wrong role.
- Private/not-found behavior.
- Validation errors.
- Edge cases.
- Regression bugs discovered during implementation.

Do not mark a step complete until the step-specific tests pass and then the full suite is run.
