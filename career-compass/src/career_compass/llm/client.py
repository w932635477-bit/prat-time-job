from __future__ import annotations

import httpx
from career_compass.config import settings


class DeepSeekClient:
    """DeepSeek V4 client using Anthropic-compatible Messages API via EvoLink."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url
        self._model = model or settings.deepseek_model

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        if settings.deepseek_thinking:
            payload["thinking"] = {"type": "enabled"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

        # Extract text from Anthropic-style content blocks
        text_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "\n".join(text_parts)

    async def chat_with_thinking(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> tuple[str, str]:
        """Returns (thinking, text) from the response."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
            "thinking": {"type": "enabled"},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

        thinking_text = ""
        response_text = ""
        for block in data.get("content", []):
            if block.get("type") == "thinking":
                thinking_text = block.get("thinking", "")
            elif block.get("type") == "text":
                response_text = block.get("text", "")

        return thinking_text, response_text
