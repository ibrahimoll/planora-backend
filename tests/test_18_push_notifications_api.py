from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import auth_headers, create_verified_user_and_login


def test_user_can_register_device_token(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushuser',
        email='pushuser@example.com',
    )

    response = client.post(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
        json={
            'token': 'firebase-device-token-example-123456789',
            'platform': 'android',
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body['token'] == 'firebase-device-token-example-123456789'
    assert body['platform'] == 'android'
    assert body['is_active'] is True


def test_user_can_list_own_device_tokens(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushlistuser',
        email='pushlistuser@example.com',
    )

    client.post(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
        json={
            'token': 'firebase-list-token-123456789',
            'platform': 'ios',
        },
    )

    response = client.get(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]['platform'] == 'ios'


def test_user_can_deactivate_own_device_token(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushdeactivateuser',
        email='pushdeactivateuser@example.com',
    )

    create_response = client.post(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
        json={
            'token': 'firebase-deactivate-token-123456789',
            'platform': 'web',
        },
    )

    device_token_id = create_response.json()['device_token_id']

    response = client.patch(
        f'/push-notifications/device-tokens/{device_token_id}/deactivate',
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['is_active'] is False


def test_user_can_heartbeat_device_token_by_id(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushheartbeatiduser',
        email='pushheartbeatiduser@example.com',
    )

    create_response = client.post(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
        json={
            'token': 'firebase-heartbeat-id-token-123456789',
            'platform': 'web',
            'device_key': 'heartbeat-device-key-id',
        },
    )

    device_token_id = create_response.json()['device_token_id']

    response = client.patch(
        '/push-notifications/device-tokens/current/heartbeat',
        headers=auth_headers(token),
        json={
            'device_token_id': device_token_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['device_token_id'] == device_token_id
    assert body['is_active'] is True


def test_user_can_heartbeat_device_token_by_device_key(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushheartbeatkeyuser',
        email='pushheartbeatkeyuser@example.com',
    )

    device_key = 'heartbeat-device-key-match'

    create_response = client.post(
        '/push-notifications/device-tokens',
        headers=auth_headers(token),
        json={
            'token': 'firebase-heartbeat-key-token-123456789',
            'platform': 'web',
            'device_key': device_key,
        },
    )

    device_token_id = create_response.json()['device_token_id']

    response = client.patch(
        '/push-notifications/device-tokens/current/heartbeat',
        headers=auth_headers(token),
        json={
            'device_key': device_key,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['device_token_id'] == device_token_id
    assert body['device_key'] == device_key
    assert body['is_active'] is True


def test_device_token_heartbeat_returns_404_for_missing_token(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='pushheartbeatmissinguser',
        email='pushheartbeatmissinguser@example.com',
    )

    response = client.patch(
        '/push-notifications/device-tokens/current/heartbeat',
        headers=auth_headers(token),
        json={
            'device_key': 'missing-device-key',
        },
    )

    assert response.status_code == 404
    assert response.json()['detail'] == 'Device token not found.'


def test_user_can_get_default_notification_preferences(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='prefuser',
        email='prefuser@example.com',
    )

    response = client.get(
        '/push-notifications/preferences',
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body['push_enabled'] is True
    assert body['task_notifications'] is True
    assert body['risk_notifications'] is True


def test_user_can_update_notification_preferences(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username='prefupdateuser',
        email='prefupdateuser@example.com',
    )

    response = client.patch(
        '/push-notifications/preferences',
        headers=auth_headers(token),
        json={
            'push_enabled': False,
            'deadline_notifications': False,
            'risk_notifications': False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['push_enabled'] is False
    assert body['deadline_notifications'] is False
    assert body['risk_notifications'] is False
    assert body['task_notifications'] is True


def test_push_routes_require_authentication(client: TestClient) -> None:
    response = client.get('/push-notifications/preferences')

    assert response.status_code == 401
