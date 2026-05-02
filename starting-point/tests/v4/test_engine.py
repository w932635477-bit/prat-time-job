from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_engine_routes_to_stage_zero(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "你做什么行业的？"

    engine = ConversationEngine(llm, msg_repo, state_repo)
    result = await engine.handle(user_id="u1", message="你好")
    assert result.stage == 0
    assert not result.is_complete


@pytest.mark.asyncio
async def test_engine_routes_to_stage_one(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    # StageOneHandler calls llm.chat, needs a plain-text return
    llm.chat.return_value = "我发现了这些可变现的知识点，你最感兴趣的是哪个？"

    # Pre-save state at stage 1
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": [{"id": "kp_1"}],
    })

    engine = ConversationEngine(llm, msg_repo, state_repo)
    result = await engine.handle(user_id="u1", message="我选第一个")
    assert result.stage == 1


@pytest.mark.asyncio
async def test_engine_returns_kit_message_at_stage_2(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()

    # Pre-save state at stage 2
    await state_repo.save("u2", 2, {
        "status": "completed",
        "product_package": {"product_name": "test"},
    })

    engine = ConversationEngine(llm, msg_repo, state_repo)
    result = await engine.handle(user_id="u2", message="查看套件")
    assert result.stage == 2
