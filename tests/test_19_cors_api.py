from __future__ import annotations

from fastapi.testclient import TestClient


ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "https://evil.example"


def test_cors_preflight_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/auth/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_simple_request_allows_configured_origin(client: TestClient) -> None:
    response = client.get(
        "/",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_blocks_unconfigured_origin(client: TestClient) -> None:
    response = client.options(
        "/auth/me",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_simple_request_does_not_allow_unconfigured_origin(
    client: TestClient,
) -> None:
    response = client.get(
        "/",
        headers={"Origin": DISALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_normal_request_without_origin_still_works(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Planora backend is running"}
    assert "access-control-allow-origin" not in response.headers
