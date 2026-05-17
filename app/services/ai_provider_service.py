from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


MAX_AI_REPLY_LENGTH = 4000


def _clean_ai_text(value: str) -> str:
    cleaned = value.strip()

    if len(cleaned) > MAX_AI_REPLY_LENGTH:
        return cleaned[:MAX_AI_REPLY_LENGTH].rstrip() + "..."

    return cleaned


def _extract_gemini_text(response_data: dict[str, Any]) -> str | None:
    candidates = response_data.get("candidates", [])

    if not candidates:
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if isinstance(text, str) and text.strip():
            return _clean_ai_text(text)

    return None


def _generate_with_gemini(prompt: str) -> str | None:
    if not settings.gemini_api_key:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 800,
        },
    }

    params = {
        "key": settings.gemini_api_key,
    }

    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            response = client.post(
                url,
                params=params,
                json=payload,
            )

            response.raise_for_status()

        return _extract_gemini_text(response.json())

    except (
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ):
        return None


def generate_ai_reply_from_provider(prompt: str) -> str | None:
    provider = settings.ai_provider.strip().lower()

    if provider == "gemini":
        return _generate_with_gemini(prompt)

    return None