from typing import Any

import httpx

from app.config import Settings


class OpenAICompatibleLLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_response(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.settings.llm_enabled or not self.settings.llm_api_key:
            return {
                "content": (
                    "I can help with library tasks, but the chat assistant is not configured yet. "
                    "Set the LLM environment variables to enable chat actions."
                ),
                "tool_calls": [],
            }

        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]
        return {
            "content": message.get("content") or "",
            "tool_calls": message.get("tool_calls") or [],
        }
