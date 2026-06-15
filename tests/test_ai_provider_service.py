from __future__ import annotations

from typing import Any

from app.services import ai_provider_service


class _GeminiResponse:
    status_code = 200
    text = "{}"

    def json(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"ok": true}',
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
            json: dict[str, Any],
        ) -> _GeminiResponse:
            calls.append({"url": url, "params": params, "json": json})
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

    generation_config = calls[0]["json"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert "responseFormat" not in generation_config
