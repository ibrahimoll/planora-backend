# Planora Step 17 Context

Date: 2026-05-16

## Status

Step 17 is completed and pushed to the repository.

Latest confirmed regression result:

- `52 passed`

## Feature

Progress Tracking and Productivity Insights.

## Endpoint

- `GET /projects/{project_id}/progress`

## Files Added or Updated

- `app/models/user_progress.py`
- `app/schemas/progress_schema.py`
- `app/services/progress_service.py`
- `app/routers/progress_routes.py`
- `app/main.py`
- `app/models/user.py`
- `app/models/project.py`
- `app/models/__init__.py`
- `tests/test_09_progress_api.py`

## Tables Used

- `projects`
- `tasks`
- `project_members`
- `users`
- `user_progress`

## Behavior

- Personal project owner can view project progress.
- Team project members can view team project progress.
- Cross-user personal project access returns `404 Project not found`.
- Missing or invalid bearer token returns `401 Unauthorized`.
- Backend calculates total tasks, completed tasks, pending tasks, overdue tasks, task status counts, hours summary, current user progress, member progress, productivity status, and recommendations.
- Backend upserts rows into `user_progress`.

## Next Recommended Step

Immediate cleanup should be the project-member role update endpoint:

- `PATCH /teams/{team_id}/projects/{project_id}/members/{user_id}`

This should update `project_members.role`, allow switching between `manager` and `member`, and should not allow assigning `owner` through normal role update.
