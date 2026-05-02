from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import Response, Request


def _make_response(body: dict, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        json=body,
        request=Request("POST", "http://test/v1/messages"),
    )


@pytest.mark.asyncio
async def test_chat_returns_text():
    from starting_point.llm.client import LLMClient

    resp_body = {
        "content": [{"type": "text", "text": "你做什么行业的？"}]
    }
    client = LLMClient(api_key="test", base_url="http://test", model="test-model")
    with patch.object(client, "_http_client") as mock_http:
        mock_http.post = AsyncMock(return_value=_make_response(resp_body))
        result = await client.chat(messages=[{"role": "user", "content": "你好"}])
    assert result == "你做什么行业的？"


@pytest.mark.asyncio
async def test_chat_raises_on_api_error():
    from starting_point.llm.client import LLMClient

    client = LLMClient(api_key="test", base_url="http://test", model="test-model")
    with patch.object(client, "_http_client") as mock_http:
        mock_http.post = AsyncMock(return_value=_make_response({}, status_code=500))
        with pytest.raises(Exception):
            await client.chat(messages=[{"role": "user", "content": "你好"}])


@pytest.mark.asyncio
async def test_chat_json_validates_and_returns_parsed():
    from starting_point.llm.client import LLMClient
    from starting_point.models import KnowledgePoint

    json_output = json.dumps({
        "knowledge_points": [
            {
                "id": "kp_1",
                "description": "A valid knowledge point description here",
                "industry": "test",
                "knowledge_type": "price_transparency",
                "target_buyer": "some target buyer group",
                "estimated_value": "saves some amount of money",
            },
            {
                "id": "kp_2",
                "description": "Another valid knowledge point description",
                "industry": "test",
                "knowledge_type": "pitfall_guide",
                "target_buyer": "another target buyer group",
                "estimated_value": "avoids costly mistakes",
            },
            {
                "id": "kp_3",
                "description": "Third valid knowledge point description",
                "industry": "test",
                "knowledge_type": "channel_info",
                "target_buyer": "yet another buyer group",
                "estimated_value": "finds better deals",
            },
        ],
        "summary": "Found three strong monetizable knowledge points from your experience",
    })
    resp_body = {
        "content": [{"type": "text", "text": f"```json\n{json_output}\n```"}]
    }
    client = LLMClient(api_key="test", base_url="http://test", model="test-model")
    with patch.object(client, "_http_client") as mock_http:
        mock_http.post = AsyncMock(return_value=_make_response(resp_body))
        result = await client.chat_json(
            messages=[{"role": "user", "content": "test"}],
            schema=KnowledgePoint,
        )
    assert "knowledge_points" in result
