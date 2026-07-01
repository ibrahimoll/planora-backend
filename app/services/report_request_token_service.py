from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import settings

REPORT_REQUEST_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _base64_url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8"))


def _secret() -> bytes:
    return settings.jwt_secret_code.encode("utf-8")


def _sign(payload: str) -> str:
    signature = hmac.new(
        _secret(),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64_url_encode(signature)


def create_report_request_token(
    *,
    project_id: int,
    requester_email: str,
    requester_name: str | None,
) -> str:
    payload = {
        "project_id": project_id,
        "requester_email": requester_email,
        "requester_name": requester_name or "",
        "iat": int(time.time()),
    }
    payload_text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_part = _base64_url_encode(payload_text.encode("utf-8"))
    signature_part = _sign(payload_part)
    return f"{payload_part}.{signature_part}"


def resolve_report_request_token(token: str) -> dict[str, Any] | None:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(payload_part)
    if not hmac.compare_digest(signature_part, expected_signature):
        return None

    try:
        payload = json.loads(_base64_url_decode(payload_part).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    issued_at = int(payload.get("iat") or 0)
    if issued_at <= 0 or int(time.time()) - issued_at > REPORT_REQUEST_TOKEN_TTL_SECONDS:
        return None

    project_id = payload.get("project_id")
    requester_email = payload.get("requester_email")

    if not isinstance(project_id, int) or project_id <= 0:
        return None
    if not isinstance(requester_email, str) or not requester_email.strip():
        return None

    return payload
