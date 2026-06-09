# AI Project Planning

Date: 2026-06-09

## Backend Behavior

Planora stores AI project plans in `ai_plans` and can create real `tasks` rows from the generated plan. The current generator is deterministic and local (`local_rule_based_v1`), so it does not require a client-side AI key or hardcoded secret.

The generator derives a project domain from the user's idea/context before selecting tasks. Clothing, ecommerce, social commerce, and other business ideas get supplier, pricing, collection, sales channel, launch, delivery, and operations tasks. Explicit software ideas still get app/product tasks. Generated task descriptions are concise task-specific blurbs and should not contain the full prompt or instruction scaffold.

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

## Preview Then Accept From Idea

The mobile AI wizard should prefer the true preview/accept flow when creating a new project from an idea. Preview does not create a project, AI plan, or tasks.

Preview request:

```http
POST /ai-plans/preview-from-idea
```

```json
{
  "project_idea": "Start a small online clothing business",
  "deadline": "2026-08-30T12:00:00Z",
  "project_type": "personal",
  "team_id": null,
  "available_hours_per_week": 8,
  "preferred_task_count": 10,
  "requirements": "Keep the first launch small and sell through Instagram.",
  "include_milestones": true
}
```

Accept request:

```http
POST /ai-plans/accept-preview
```

```json
{
  "preview": {
    "source": "local_rule_based_v1",
    "domain": "business",
    "project_title": "Start a small online clothing business",
    "description": "A practical launch plan for the project idea.",
    "project_type": "personal",
    "team_id": null,
    "deadline": "2026-08-30T12:00:00Z",
    "summary": "Previewed a structured plan with 10 tasks before the deadline.",
    "tasks": [
      {
        "suggested_order": 1,
        "title": "Define clothing niche and target customer",
        "description": "Clarify who the first collection serves, what style it offers, and what makes it worth buying.",
        "priority": "high",
        "estimated_hours": 2.0,
        "status": "todo",
        "due_date": "2026-06-16T12:00:00Z",
        "assigned_to": null
      }
    ],
    "milestones": [],
    "risks": [],
    "recommendations": [],
    "project_idea": "Start a small online clothing business",
    "requirements": "Keep the first launch small and sell through Instagram.",
    "available_hours_per_week": 8,
    "preferred_task_count": 10
  }
}
```

Accept should send back the preview object returned by the preview endpoint, including any client-side edits to task titles/descriptions. It creates the personal or team project, saves the AI plan, and creates the accepted tasks. Team previews require team membership; team accept requires project-create/manage permission.

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
- AI project wizard: calls `/ai-plans/preview-from-idea` first, then `/ai-plans/accept-preview` only after the user accepts the plan.
- Planora AI Chat: `Plan` action generates tasks for the selected project without pretending the planning endpoint is chat history.

## Limitations

- The current generator is rule-based fallback logic, not a remote LLM call.
- Backend pytest requires a local Python environment with backend dependencies installed and `TEST_DATABASE_URL` configured.
- Mobile still needs emulator/device visual QA for the generated-task flows.
