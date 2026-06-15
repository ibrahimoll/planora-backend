from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.routers.ai_plan_stable_routes import stable_preview_ai_plan_from_idea
from app.schemas.ai_plan_schema import AIPlanPreviewRequest
from app.schemas.project_schema import ProjectType


class _User:
    user_id = 1


def _pushup_request() -> AIPlanPreviewRequest:
    return AIPlanPreviewRequest(
        project_idea="Do 100 pushup a day",
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        project_type=ProjectType.personal,
        available_hours_per_week=5,
        preferred_task_count=8,
    )


def _stable_pushup_preview():
    return stable_preview_ai_plan_from_idea(
        preview_data=_pushup_request(),
        db=None,
        current_user=_User(),
    )


def test_stable_preview_pushup_returns_fitness_health_domain():
    preview = _stable_pushup_preview()

    assert preview.success is True
    assert preview.domain == "fitness_health"
    assert preview.ai_generation_status == "generated"


def test_stable_preview_pushup_tasks_are_fitness_specific():
    preview = _stable_pushup_preview()
    titles = [task.title for task in preview.tasks]
    combined = " ".join([*titles, *(task.description or "" for task in preview.tasks)]).lower()

    assert titles == [
        "Test your current max pushups",
        "Set a safe daily starting volume",
        "Split pushups into manageable sets",
        "Practice correct pushup form",
        "Create a 2-week progression schedule",
        "Add recovery and pain rules",
        "Track reps, sets, and difficulty",
        "Review progress after 14 days",
    ]
    assert "pushup" in combined
    assert "form" in combined
    assert "progression" in combined
    assert "recovery" in combined
    assert "track" in combined or "tracking" in combined


def test_stable_preview_pushup_avoids_product_management_language():
    preview = _stable_pushup_preview()
    response_text = " ".join(
        [
            preview.summary,
            preview.description or "",
            *[task.title for task in preview.tasks],
            *[(task.description or "") for task in preview.tasks],
            *[milestone.get("description", "") for milestone in preview.milestones],
            *[risk.get("risk", "") for risk in preview.risks],
            *[risk.get("recommendation", "") for risk in preview.risks],
            *preview.recommendations,
        ]
    ).lower()

    for forbidden in (
        "customer benefit",
        "requirements",
        "features",
        "mvp",
        "first useful version",
        "core flow",
    ):
        assert forbidden not in response_text


def test_stable_preview_summary_count_matches_actual_task_count():
    preview = _stable_pushup_preview()
    match = re.search(r"\b(\d+)\s+tasks?\b", preview.summary)

    assert match is not None
    assert int(match.group(1)) == len(preview.tasks)
    assert preview.preferred_task_count == len(preview.tasks)
