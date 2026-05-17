from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_AI_REPLY_LENGTH = 4000


def _clean_ai_text(value: str) -> str:
    cleaned = value.strip()

    if len(cleaned) > MAX_AI_REPLY_LENGTH:
        return cleaned[:MAX_AI_REPLY_LENGTH].rstrip() + "..."

    return cleaned


def _extract_gemini_text(response_data: dict[str, Any]) -> str | None:
    candidates = response_data.get("candidates", [])

    if not candidates:
        logger.warning(
            "Gemini response did not include candidates. response_keys=%s",
            sorted(response_data.keys()),
        )
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if isinstance(text, str) and text.strip():
            return _clean_ai_text(text)

    logger.warning("Gemini response did not include text parts.")

    return None


def _generate_with_gemini(prompt: str) -> str | None:
    if not settings.gemini_api_key:
        logger.warning("Gemini API key is missing. Falling back to local AI.")
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

        if response.status_code >= 400:
            logger.warning(
                "Gemini API error. status=%s. Falling back to local AI.",
                response.status_code,
            )
            return None

        return _extract_gemini_text(response.json())

    except httpx.TimeoutException as exc:
        logger.warning("Gemini API timeout: %s", type(exc).__name__)
        return None

    except httpx.HTTPError as exc:
        logger.warning("Gemini HTTP error: %s", type(exc).__name__)
        return None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Gemini response parsing error: %s", type(exc).__name__)
        return None


def generate_ai_reply_from_provider(prompt: str) -> str | None:
    provider = settings.ai_provider.strip().lower()

    if provider == "gemini":
        return _generate_with_gemini(prompt)

    return None
