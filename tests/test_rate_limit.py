from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.rate_limit import check_rate_limit


def test_rate_limit_blocks_after_limit():
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    check_rate_limit(
        request,
        "test-rate-limit",
        limit=2,
        window_seconds=60,
        identifier="user@example.com",
    )
    check_rate_limit(
        request,
        "test-rate-limit",
        limit=2,
        window_seconds=60,
        identifier="user@example.com",
    )

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(
            request,
            "test-rate-limit",
            limit=2,
            window_seconds=60,
            identifier="user@example.com",
        )

    assert exc_info.value.status_code == 429
