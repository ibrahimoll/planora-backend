from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status

_requests: dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"

    return request.client.host


def _safe_identifier(identifier: str | None) -> str:
    if not identifier:
        return ""

    normalized = identifier.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def check_rate_limit(
    request: Request,
    action: str,
    *,
    limit: int,
    window_seconds: int,
    identifier: str | None = None,
) -> None:
    now = time.monotonic()
    identity = _safe_identifier(identifier)
    key = f"{action}:{_client_key(request)}:{identity}"
    bucket = _requests[key]
    window_start = now - window_seconds

    while bucket and bucket[0] <= window_start:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )

    bucket.append(now)
