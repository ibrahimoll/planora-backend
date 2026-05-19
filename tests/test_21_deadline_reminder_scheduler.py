from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

import app.services.notification_service as notification_service
from app.models.notification import Notification
from app.models.task import Task
from app.services.deadline_reminder_service import run_deadline_reminder_scan
from app.services.notification_service import create_notification, send_push_for_notification
from tests.conftest import (
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_notification_push_can_be_sent_after_manual_commit(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    user_id, _token = create_verified_user_and_login(
        client,
        db,
        username="pushaftercommituser",
        email="pushaftercommituser@example.com",
    )

    sent: list[dict[str, Any]] = []

    def fake_send_push_to_user(**kwargs):
        sent.append(kwargs)
        return None

    monkeypatch.setattr(
        notification_service,
        "send_push_to_user",
        fake_send_push_to_user,
    )

    notification = create_notification(
        db=db,
        user_id=user_id,
        title="Manual commit push",
        message="This push should be sent after commit.",
        notification_type="deadline",
        commit=False,
        send_push=False,
    )

    db.commit()

    send_push_for_notification(
        db=db,
        notification=notification,
    )

    assert len(sent) == 1
    assert sent[0]["user_id"] == user_id
    assert sent[0]["notification_type"] == "deadline"
    assert sent[0]["data"]["notification_id"] == notification.notification_id


def test_deadline_scan_sends_push_after_scan_commit(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    user_id, token = create_verified_user_and_login(
        client,
        db,
        username="deadlinescheduleruser",
        email="deadlinescheduleruser@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Scheduler Deadline Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Scheduler Due Soon Task",
    )

    task_row = db.get(Task, task["task_id"])
    assert task_row is not None

    task_row.assigned_to = user_id
    task_row.due_date = datetime.now(timezone.utc) + timedelta(hours=1)
    task_row.status = "todo"
    db.commit()

    sent: list[dict[str, Any]] = []

    def fake_send_push_to_user(**kwargs):
        sent.append(kwargs)
        return None

    monkeypatch.setattr(
        notification_service,
        "send_push_to_user",
        fake_send_push_to_user,
    )

    result = run_deadline_reminder_scan(
        db=db,
        hours_ahead=24,
        include_overdue=True,
    )

    assert result["due_soon_created"] == 1
    assert result["overdue_created"] == 0
    assert result["total_created"] == 1

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.type == "deadline",
        )
        .all()
    )

    assert len(notifications) == 1
    assert len(sent) == 1
    assert sent[0]["user_id"] == user_id
    assert sent[0]["notification_type"] == "deadline"
    assert sent[0]["data"]["notification_id"] == notifications[0].notification_id
