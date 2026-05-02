from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from starting_point.models import KnowledgePoint, StageZeroOutput


def _make_kps(n: int) -> list[dict]:
    return [
        {
            "id": f"kp_{i}",
            "description": f"Valid knowledge point description number {i} about industry",
            "industry": "test",
            "knowledge_type": "price_transparency",
            "target_buyer": f"target buyer group {i}",
            "estimated_value": f"saves money option {i}",
        }
        for i in range(1, n + 1)
    ]


def _json_response(kps: list[dict], summary: str = "Found monetizable points from your experience") -> str:
    output = {"knowledge_points": kps, "summary": summary}
    return f"```json\n{json.dumps(output, ensure_ascii=False)}\n```"


@pytest.mark.asyncio
async def test_normal_flow_text_then_json(db):
    """Stage 0: user sends 5 messages, LLM outputs JSON at turn 5."""
    from starting_point.stages.stage_zero import StageZeroHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()

    # First 4 turns: LLM asks questions (plain text)
    llm.chat.side_effect = [
        "你做什么行业的？",
        "在这个行业里，你比别人更懂什么？",
        "有没有朋友经常问你某个问题？",
        "你有没有帮别人省钱的经历？",
    ]

    handler = StageZeroHandler(llm, msg_repo, state_repo)
    user_id = "test-user"

    for msg in ["你好", "建材", "价格", "有"]:
        result = await handler.handle(user_id=user_id, message=msg)
        assert not result.is_complete

    # Turn 5: LLM outputs JSON with 3+ knowledge points
    llm.chat.side_effect = None
    llm.chat.return_value = _json_response(_make_kps(3))
    result = await handler.handle(user_id=user_id, message="我帮朋友省了很多钱")
    assert result.is_complete
    assert result.stage == 1
    assert "knowledge_points" in result.stage_data


@pytest.mark.asyncio
async def test_hard_cap_forces_extraction(db):
    """After 10 user messages, force extraction mode triggers."""
    from starting_point.stages.stage_zero import StageZeroHandler, MAX_STAGE0_MESSAGES
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "继续聊聊"  # LLM never outputs JSON

    handler = StageZeroHandler(llm, msg_repo, state_repo)
    user_id = "test-user"

    for i in range(MAX_STAGE0_MESSAGES):
        result = await handler.handle(user_id=user_id, message=f"message {i}")

    # After MAX messages, force extraction triggers
    llm.chat.return_value = _json_response(_make_kps(3))
    result = await handler.handle(user_id=user_id, message="last message")
    assert result.is_complete


@pytest.mark.asyncio
async def test_early_json_with_fewer_than_3_points(db):
    """LLM outputs JSON too early with < 3 points -> handler continues."""
    from starting_point.stages.stage_zero import StageZeroHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()

    # Turn 1: LLM tries to output JSON with only 2 points
    llm.chat.side_effect = [
        _json_response(_make_kps(2), summary="short"),
        "你还有什么其他经验？",  # After detecting < 3 points, continues
    ]

    handler = StageZeroHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="test")
    # Should NOT complete because only 2 points
    assert not result.is_complete


@pytest.mark.asyncio
async def test_resume_mid_conversation(db):
    """User returns mid-conversation, state loads correctly."""
    from starting_point.stages.stage_zero import StageZeroHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)

    # Pre-save some messages
    await msg_repo.save("u1", "user", "我在建材行业", 0)
    await msg_repo.save("u1", "assistant", "你做了多少年？", 0)
    await state_repo.save("u1", 0, {"user_message_count": 1, "status": "collecting"})

    llm = AsyncMock()
    llm.chat.return_value = "15年了，那你对价格方面很了解吧？"
    handler = StageZeroHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="15年")
    assert not result.is_complete
