from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

import app.services.firebase_push_service as firebase_push_service
from app.models.device_token import DeviceToken
from tests.conftest import auth_headers, create_verified_user_and_login


def _register_device_token(
    client: TestClient,
    token: str,
    fcm_token: str,
    platform: str = "android",
) -> None:
    response = client.post(
        "/push-notifications/device-tokens",
        headers=auth_headers(token),
        json={
            "token": fcm_token,
            "platform": platform,
        },
    )

    assert response.status_code == 201, response.text


def test_firebase_push_status_endpoint(client: TestClient) -> None:
    response = client.get("/push-notifications/status")

    assert response.status_code == 200

    body = response.json()
    assert "firebase_enabled" in body
    assert "firebase_configured" in body
    assert "message" in body


def test_test_push_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/push-notifications/test",
        json={
            "title": "Test Push",
            "message": "This should require authentication.",
            "notification_type": "system",
        },
    )

    assert response.status_code == 401


def test_user_can_send_test_push_to_active_device_token(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="firebasepushuser",
        email="firebasepushuser@example.com",
    )

    _register_device_token(
        client=client,
        token=token,
        fcm_token="valid-firebase-token-123456789",
    )

    sent_messages = []

    monkeypatch.setattr(firebase_push_service.settings, "firebase_enabled", True)
    monkeypatch.setattr(firebase_push_service, "initialize_firebase_app", lambda: True)

    def fake_send(message):
        sent_messages.append(message)
        return "firebase-message-id"

    monkeypatch.setattr(firebase_push_service.messaging, "send", fake_send)

    response = client.post(
        "/push-notifications/test",
        headers=auth_headers(token),
        json={
            "title": "Planora Test",
            "message": "Firebase test push.",
            "notification_type": "system",
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "sent"
    assert body["sent_count"] == 1
    assert body["failed_count"] == 0
    assert len(sent_messages) == 1


def test_push_is_skipped_when_preferences_disable_push(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="firebaseprefuser",
        email="firebaseprefuser@example.com",
    )

    _register_device_token(
        client=client,
        token=token,
        fcm_token="preference-disabled-token-123456789",
    )

    pref_response = client.patch(
        "/push-notifications/preferences",
        headers=auth_headers(token),
        json={
            "push_enabled": False,
        },
    )

    assert pref_response.status_code == 200, pref_response.text

    sent_messages = []

    monkeypatch.setattr(firebase_push_service.settings, "firebase_enabled", True)
    monkeypatch.setattr(firebase_push_service, "initialize_firebase_app", lambda: True)

    def fake_send(message):
        sent_messages.append(message)
        return "firebase-message-id"

    monkeypatch.setattr(firebase_push_service.messaging, "send", fake_send)

    response = client.post(
        "/push-notifications/test",
        headers=auth_headers(token),
        json={
            "title": "Should Skip",
            "message": "User disabled push.",
            "notification_type": "system",
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "skipped"
    assert body["sent_count"] == 0
    assert body["skipped_count"] == 1
    assert sent_messages == []


def test_invalid_firebase_token_is_deactivated(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="firebaseinvaliduser",
        email="firebaseinvaliduser@example.com",
    )

    invalid_token = "invalid-firebase-token-123456789"

    _register_device_token(
        client=client,
        token=token,
        fcm_token=invalid_token,
    )

    class InvalidArgumentError(Exception):
        pass

    monkeypatch.setattr(firebase_push_service.settings, "firebase_enabled", True)
    monkeypatch.setattr(firebase_push_service, "initialize_firebase_app", lambda: True)

    def fake_send(_message):
        raise InvalidArgumentError("Invalid registration token")

    monkeypatch.setattr(firebase_push_service.messaging, "send", fake_send)

    response = client.post(
        "/push-notifications/test",
        headers=auth_headers(token),
        json={
            "title": "Invalid Token",
            "message": "This token should be deactivated.",
            "notification_type": "system",
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "failed"
    assert body["sent_count"] == 0
    assert body["failed_count"] == 1
    assert body["deactivated_tokens"] == 1

    db.expire_all()

    device_token = db.execute(
        select(DeviceToken).where(DeviceToken.token == invalid_token)
    ).scalars().first()

    assert device_token is not None
    assert device_token.is_active is False
