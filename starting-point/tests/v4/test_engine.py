from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_engine_routes_to_stage_zero(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "你做什么行业的？"

    kit_repo = KitRepo(db)
    engine = ConversationEngine(llm, msg_repo, state_repo, kit_repo)
    result = await engine.handle(user_id="u1", message="你好")
    assert result.stage == 0
    assert not result.is_complete


@pytest.mark.asyncio
async def test_engine_routes_to_stage_one(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    # StageOneHandler calls llm.chat, needs a plain-text return
    llm.chat.return_value = "我发现了这些可变现的知识点，你最感兴趣的是哪个？"

    # Pre-save state at stage 1
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": [{"id": "kp_1"}],
    })

    engine = ConversationEngine(llm, msg_repo, state_repo, kit_repo)
    result = await engine.handle(user_id="u1", message="我选第一个")
    assert result.stage == 1


@pytest.mark.asyncio
async def test_engine_routes_to_stage_two_handler(db):
    from starting_point.stages.engine import ConversationEngine
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "你可以参考第1天的日历内容，直接复制发布就行。"

    # Pre-save state at stage 2
    await state_repo.save("u2", 2, {
        "status": "completed",
        "product_package": {"product_name": "test"},
    })

    engine = ConversationEngine(llm, msg_repo, state_repo, kit_repo)
    result = await engine.handle(
        user_id="u2",
        message="我今天该发什么",
        tier="standard",
    )
    assert result.stage == 2
    assert "日历" in result.message or "发布" in result.message
