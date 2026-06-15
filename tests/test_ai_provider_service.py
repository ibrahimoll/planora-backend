from __future__ import annotations

from typing import Any

from app.services import ai_provider_service


class _GeminiResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "{}",
        response_text: str = '{"ok": true}',
    ):
        self.status_code = status_code
        self.text = text
        self.response_text = response_text

    def json(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": self.response_text,
                            }
                        ]
                    }
                }
            ]
        }


def test_gemini_json_mode_uses_response_mime_type(monkeypatch):
    calls: list[dict[str, Any]] = []

    class GeminiClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        def __enter__(self) -> "GeminiClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            params: dict[str, str],
            headers: dict[str, str],
            json: dict[str, Any],
        ) -> _GeminiResponse:
            calls.append({"url": url, "params": params, "headers": headers, "json": json})
            return _GeminiResponse()

    monkeypatch.setattr(ai_provider_service.settings, "ai_provider", "gemini")
    monkeypatch.setattr(ai_provider_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_provider_service.httpx, "Client", GeminiClient)

    reply = ai_provider_service.generate_ai_reply_from_provider(
        "Return a JSON object.",
        response_mime_type="application/json",
        use_local_fallback=False,
    )

    assert reply == '{"ok": true}'
    assert len(calls) == 1
    assert calls[0]["params"] == {}
    assert calls[0]["headers"] == {"x-goog-api-key": "test-key"}
    assert "test-key" not in calls[0]["url"]

    generation_config = calls[0]["json"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert "responseFormat" not in generation_config


def test_gemini_json_mode_400_retries_without_response_mime_type(monkeypatch):
    calls: list[dict[str, Any]] = []

    class GeminiClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        def __enter__(self) -> "GeminiClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            params: dict[str, str],
            headers: dict[str, str],
            json: dict[str, Any],
        ) -> _GeminiResponse:
            calls.append({"url": url, "params": params, "headers": headers, "json": json})

            if len(calls) == 1:
                return _GeminiResponse(
                    status_code=400,
                    text="responseMimeType is not supported for this model",
                )

            return _GeminiResponse(response_text='{"retried": true}')

    monkeypatch.setattr(ai_provider_service.settings, "ai_provider", "gemini")
    monkeypatch.setattr(ai_provider_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_provider_service.httpx, "Client", GeminiClient)

    reply = ai_provider_service.generate_ai_reply_from_provider(
        "Return a JSON object.",
        response_mime_type="application/json",
        use_local_fallback=False,
    )

    assert reply == '{"retried": true}'
    assert len(calls) == 2
    assert all(call["params"] == {} for call in calls)
    assert all(call["headers"] == {"x-goog-api-key": "test-key"} for call in calls)
    assert all("test-key" not in call["url"] for call in calls)
    assert calls[0]["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseMimeType" not in calls[1]["json"]["generationConfig"]
