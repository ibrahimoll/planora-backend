# AI Project Planning

Date: 2026-06-07

## Backend Behavior

Planora stores AI project plans in `ai_plans` and can create real `tasks` rows from the generated plan. The current generator is deterministic and local (`local_rule_based_v1`), so it does not require a client-side AI key or hardcoded secret.

Generated task data respects the backend task constraints:

- `priority`: `low`, `medium`, or `high`
- `status`: starts as `todo`
- `estimated_hours`: non-negative
- `due_date`: scheduled before or at the project deadline
- team projects may assign generated tasks across project members

## Generate And Create Tasks

Personal project:

```http
POST /projects/{project_id}/ai-plan/generate
```

Team project:

```http
POST /teams/{team_id}/projects/{project_id}/ai-plan/generate
```

Request body:

```json
{
  "prompt": "Create a practical launch plan for the mobile app.",
  "generate_tasks": true,
  "overwrite_existing_tasks": false,
  "preferred_task_count": 8,
  "include_milestones": true
}
```

Response body:

```json
{
  "project_id": 42,
  "plan_id": 15,
  "summary": "Generated a structured plan for 'Mobile Launch' with 8 tasks before the project deadline.",
  "tasks_created": 8,
  "tasks": [
    {
      "task_id": 101,
      "title": "Define scope and success criteria",
      "description": "For project 'Mobile Launch', complete this step based on: ...",
      "priority": "high",
      "estimated_hours": 2.0,
      "status": "todo",
      "due_date": "2026-06-14T10:00:00+00:00"
    }
  ]
}
```

## Plan Only

Set `generate_tasks` to `false` to save an AI plan without creating tasks:

```json
{
  "prompt": "Only create a planning outline.",
  "generate_tasks": false,
  "preferred_task_count": 5
}
```

The response returns `tasks_created: 0` and an empty `tasks` list, while the full generated plan remains saved in `ai_plans.generated_plan`.

## Compatibility Routes

The older AI plan routes remain available:

- `POST /projects/{project_id}/ai-plans`
- `GET /projects/{project_id}/ai-plans`
- `POST /teams/{team_id}/projects/{project_id}/ai-plans`
- `GET /teams/{team_id}/projects/{project_id}/ai-plans`

Those routes return the stored `AIPlanResponse` shape. The newer `/ai-plan/generate` routes return the mobile-friendly `AIPlanGenerateResponse` with the created task summary.

## Mobile Trigger Points

The Flutter app calls `/ai-plan/generate` from:

- Project Details: generate, append, or replace tasks for the currently opened project.
- Create Project: optional AI Tasks toggle creates tasks immediately after the project row is created.
- Planora AI Chat: `Plan` action generates tasks for the selected project without pretending the planning endpoint is chat history.

## Limitations

- The current generator is rule-based fallback logic, not a remote LLM call.
- Backend pytest requires a local Python environment with backend dependencies installed and `TEST_DATABASE_URL` configured.
- Mobile still needs emulator/device visual QA for the generated-task flows.
