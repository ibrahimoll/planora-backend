from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.task import Task
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
    make_admin_directly,
)


def set_task_due_date(db: Session, task_id: int, due_date: datetime) -> None:
    task = db.get(Task, task_id)
    assert task is not None

    task.due_date = due_date
    db.commit()


def complete_task_directly(db: Session, task_id: int) -> None:
    task = db.get(Task, task_id)
    assert task is not None

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()


def test_non_admin_cannot_run_deadline_scan(client: TestClient, db: Session) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="deadlineuser",
        email="deadlineuser@example.com",
    )

    response = client.post(
        "/deadline-reminders/run",
        headers=auth_headers(token),
        json={
            "hours_ahead": 24,
            "include_overdue": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_deadline_scan_creates_due_soon_and_overdue_reminders(
    client: TestClient,
    db: Session,
) -> None:
    _admin_id, admin_token = create_verified_user_and_login(
        client,
        db,
        username="deadlineadmin",
        email="deadlineadmin@example.com",
    )
    make_admin_directly(db, "deadlineadmin@example.com")

    _user_id, user_token = create_verified_user_and_login(
        client,
        db,
        username="deadlinetaskuser",
        email="deadlinetaskuser@example.com",
    )

    project = create_personal_project(client, user_token, title="Deadline Project")

    due_soon_task = create_personal_task(
        client,
        user_token,
        project_id=project["project_id"],
        title="Due Soon Task",
    )
    overdue_task = create_personal_task(
        client,
        user_token,
        project_id=project["project_id"],
        title="Overdue Task",
    )

    now = datetime.now(timezone.utc)
    set_task_due_date(
        db,
        due_soon_task["task_id"],
        now + timedelta(hours=2),
    )
    set_task_due_date(
        db,
        overdue_task["task_id"],
        now - timedelta(hours=2),
    )

    run_response = client.post(
        "/deadline-reminders/run",
        headers=auth_headers(admin_token),
        json={
            "hours_ahead": 24,
            "include_overdue": True,
        },
    )

    assert run_response.status_code == 200
    assert run_response.json() == {
        "due_soon_created": 1,
        "overdue_created": 1,
        "total_created": 2,
    }

    notifications_response = client.get(
        "/notifications?unread_only=true",
        headers=auth_headers(user_token),
    )

    assert notifications_response.status_code == 200
    deadline_notifications = [
        notification
        for notification in notifications_response.json()
        if notification["type"] == "deadline"
    ]
    assert len(deadline_notifications) == 2

    reminders_response = client.get(
        "/deadline-reminders/me",
        headers=auth_headers(user_token),
    )

    assert reminders_response.status_code == 200
    reminder_types = {reminder["reminder_type"] for reminder in reminders_response.json()}
    assert reminder_types == {"due_soon", "overdue"}


def test_deadline_scan_does_not_create_duplicate_reminders(
    client: TestClient,
    db: Session,
) -> None:
    _admin_id, admin_token = create_verified_user_and_login(
        client,
        db,
        username="duplicatedeadlineadmin",
        email="duplicatedeadlineadmin@example.com",
    )
    make_admin_directly(db, "duplicatedeadlineadmin@example.com")

    _user_id, user_token = create_verified_user_and_login(
        client,
        db,
        username="duplicatedeadlineuser",
        email="duplicatedeadlineuser@example.com",
    )

    project = create_personal_project(client, user_token, title="Duplicate Deadline Project")
    task = create_personal_task(
        client,
        user_token,
        project_id=project["project_id"],
        title="Duplicate Reminder Task",
    )

    set_task_due_date(
        db,
        task["task_id"],
        datetime.now(timezone.utc) + timedelta(hours=2),
    )

    first_response = client.post(
        "/deadline-reminders/run",
        headers=auth_headers(admin_token),
        json={
            "hours_ahead": 24,
            "include_overdue": True,
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["total_created"] == 1

    second_response = client.post(
        "/deadline-reminders/run",
        headers=auth_headers(admin_token),
        json={
            "hours_ahead": 24,
            "include_overdue": True,
        },
    )

    assert second_response.status_code == 200
    assert second_response.json() == {
        "due_soon_created": 0,
        "overdue_created": 0,
        "total_created": 0,
    }


def test_deadline_scan_ignores_completed_tasks(client: TestClient, db: Session) -> None:
    _admin_id, admin_token = create_verified_user_and_login(
        client,
        db,
        username="completeddeadlineadmin",
        email="completeddeadlineadmin@example.com",
    )
    make_admin_directly(db, "completeddeadlineadmin@example.com")

    _user_id, user_token = create_verified_user_and_login(
        client,
        db,
        username="completeddeadlineuser",
        email="completeddeadlineuser@example.com",
    )

    project = create_personal_project(client, user_token, title="Completed Deadline Project")
    task = create_personal_task(
        client,
        user_token,
        project_id=project["project_id"],
        title="Completed Deadline Task",
    )

    set_task_due_date(
        db,
        task["task_id"],
        datetime.now(timezone.utc) + timedelta(hours=2),
    )
    complete_task_directly(db, task["task_id"])

    response = client.post(
        "/deadline-reminders/run",
        headers=auth_headers(admin_token),
        json={
            "hours_ahead": 24,
            "include_overdue": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "due_soon_created": 0,
        "overdue_created": 0,
        "total_created": 0,
    }
