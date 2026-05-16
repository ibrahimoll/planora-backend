# Planora Lint Cleanup Notes

Date: 2026-05-16

## Deadline Reminder Route Cleanup

File:

```text
app/routers/deadline_reminder_routes.py
```

Cleanup completed:

- Fixed SonarLint `python:S8410` warning on the `limit` query parameter in `list_my_deadline_reminders`.
- Replaced direct `Query(default=50, ge=1, le=100)` usage in the function signature with an `Annotated` alias.

Correct pattern now used:

```python
DeadlineReminderLimitQuery = Annotated[int, Query(ge=1, le=100)]


def list_my_deadline_reminders(
    db: DBSession,
    current_user: CurrentUser,
    limit: DeadlineReminderLimitQuery = 50,
):
    return get_my_deadline_reminders(
        db=db,
        current_user=current_user,
        limit=limit,
    )
```

Important FastAPI rule:

- When using `Annotated[..., Query(...)]`, do not put the default value inside `Query(default=...)`.
- Put the default value on the function parameter instead.

Correct:

```python
LimitQuery = Annotated[int, Query(ge=1, le=100)]
limit: LimitQuery = 50
```

Avoid:

```python
LimitQuery = Annotated[int, Query(default=50, ge=1, le=100)]
limit: LimitQuery
```

Reason:

- FastAPI can raise a startup error when defaults are placed inside `Query()` while using `Annotated`.
- This same rule was also applied earlier to `activity_log_routes.py` for Step 16.

Current repo status:

- GitHub file already contains the fixed `DeadlineReminderLimitQuery` pattern.
- User confirmed the local fix was done.
