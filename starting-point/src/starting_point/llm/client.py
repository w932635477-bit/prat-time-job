from __future__ import annotations

import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from starting_point.config import settings
from starting_point.utils.json import extract_json

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_JSON_RETRIES = 3


class LLMClient:
    """DeepSeek client using Anthropic-compatible Messages API via EvoLink."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url
        self._model = model or settings.deepseek_model
        self._http_client = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._http_client.aclose()

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        payload = self._build_payload(messages, system, temperature, max_tokens)
        response = await self._http_client.post(
            f"{self._base_url}/v1/messages",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        return self._extract_text(response.json())

    async def chat_json(
        self,
        messages: list[dict],
        schema: type[T],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> T:
        """Chat with JSON extraction + Pydantic validation + retry."""
        for attempt in range(MAX_JSON_RETRIES):
            text = await self.chat(messages, system, temperature, max_tokens)
            parsed = self._extract_json(text)
            if parsed is not None:
                try:
                    return schema.model_validate(parsed)
                except ValidationError as e:
                    logger.warning(
                        "LLM JSON validation failed (attempt %d/%d): %s",
                        attempt + 1,
                        MAX_JSON_RETRIES,
                        e,
                    )
                    continue
            logger.warning(
                "LLM JSON parse failed (attempt %d/%d)",
                attempt + 1,
                MAX_JSON_RETRIES,
            )
        raise ValueError(
            f"Failed to extract valid JSON after {MAX_JSON_RETRIES} attempts"
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[dict],
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        payload: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        return payload

    @staticmethod
    def _extract_text(data: dict) -> str:
        parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)

    _extract_json = staticmethod(extract_json)
