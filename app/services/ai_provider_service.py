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
        print("[GEMINI PARSE ERROR] No candidates found.")
        print("[GEMINI RAW RESPONSE]", response_data)
        logger.warning("Gemini response did not include candidates: %s", response_data)
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if isinstance(text, str) and text.strip():
            return _clean_ai_text(text)

    print("[GEMINI PARSE ERROR] No text parts found.")
    print("[GEMINI RAW RESPONSE]", response_data)
    logger.warning("Gemini response did not include text parts: %s", response_data)

    return None


def _generate_with_gemini(prompt: str) -> str | None:
    if not settings.gemini_api_key:
        print("[GEMINI CONFIG ERROR] GEMINI_API_KEY is missing.")
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
        print("[GEMINI REQUEST] Sending request to Gemini...")
        print("[GEMINI MODEL]", settings.gemini_model)
        print("[GEMINI TIMEOUT]", settings.gemini_timeout_seconds)

        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            response = client.post(
                url,
                params=params,
                json=payload,
            )

        print("[GEMINI STATUS]", response.status_code)
        print("[GEMINI BODY]", response.text[:1500])

        if response.status_code >= 400:
            logger.warning(
                "Gemini API error. status=%s body=%s",
                response.status_code,
                response.text,
            )
            return None

        return _extract_gemini_text(response.json())

    except httpx.TimeoutException as exc:
        print(f"[GEMINI TIMEOUT ERROR] {type(exc).__name__}: {exc}")
        logger.warning("Gemini API timeout: %s", exc)
        return None

    except httpx.HTTPError as exc:
        print(f"[GEMINI HTTP ERROR] {type(exc).__name__}: {exc}")
        logger.warning("Gemini HTTP error: %s", exc)
        return None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[GEMINI PARSING ERROR] {type(exc).__name__}: {exc}")
        logger.warning("Gemini response parsing error: %s", exc)
        return None


def generate_ai_reply_from_provider(prompt: str) -> str | None:
    provider = settings.ai_provider.strip().lower()

    print(
        "[AI DEBUG]",
        "provider=", provider,
        "has_key=", bool(settings.gemini_api_key),
        "model=", settings.gemini_model,
        "timeout=", settings.gemini_timeout_seconds,
    )

    if provider == "gemini":
        return _generate_with_gemini(prompt)

    print("[AI DEBUG] Provider is not gemini. Falling back to local rule-based AI.")
    return None