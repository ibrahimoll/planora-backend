from __future__ import annotations
import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_owner_can_export_personal_project_report(
    client: TestClient,
    db: Session,
):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_owner",
        email="report_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Step 15 Report Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Step 15 Report Task",
    )

    response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project"]["project_id"] == project["project_id"]
    assert data["project"]["title"] == "Step 15 Report Project"
    assert data["project"]["project_type"] == "personal"

    assert data["progress"]["total_tasks"] == 1
    assert data["progress"]["completed_tasks"] == 0
    assert data["progress"]["pending_tasks"] == 1
    assert data["progress"]["completion_percentage"] == pytest.approx(0.0)
    assert data["task_status_counts"]["todo"] == 1
    assert data["task_priority_counts"]["medium"] == 1

    assert data["members"][0]["user_id"] == user_id
    assert data["members"][0]["role"] == "owner"

    assert data["tasks"][0]["task_id"] == task["task_id"]
    assert data["tasks"][0]["title"] == "Step 15 Report Task"


def test_user_cannot_export_other_users_personal_project_report(
    client: TestClient,
    db: Session,
):
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_owner_two",
        email="report_owner_two@example.com",
    )

    _, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_other_user",
        email="report_other_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Report Project",
    )

    response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_unauthenticated_user_cannot_export_report(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_auth_owner",
        email="report_auth_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Auth Required Report Project",
    )

    response = client.get(
        f"/reports/projects/{project['project_id']}",
    )

    assert response.status_code == 401