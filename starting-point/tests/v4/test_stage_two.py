from __future__ import annotations

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_stage_two_handler_returns_coaching_response(db):
    from starting_point.stages.stage_two import StageTwoHandler
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "你可以参考日历第1天的内容，直接复制发布就行。"

    handler = StageTwoHandler(llm, msg_repo, state_repo, kit_repo)
    result = await handler.handle("u1", "我今天该发什么")
    assert result.stage == 2
    assert not result.is_complete


@pytest.mark.asyncio
async def test_stage_two_handler_negative_emotion_injects_empathy(db):
    from starting_point.stages.stage_two import StageTwoHandler
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "我理解你的感受，你已经有了很好的起步。"

    handler = StageTwoHandler(llm, msg_repo, state_repo, kit_repo)
    await handler.handle("u1", "算了，我不想做了")

    # Verify the system prompt includes empathy instructions
    call_args = llm.chat.call_args
    system = call_args.kwargs.get("system", "")
    assert "情绪低落" in system or "共情" in system


@pytest.mark.asyncio
async def test_stage_two_handler_builds_kit_summary(db):
    from starting_point.stages.stage_two import StageTwoHandler
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "试试看这样改..."

    handler = StageTwoHandler(llm, msg_repo, state_repo, kit_repo)
    kit = {
        "product_package": {
            "product_name": "装修避坑指南",
            "price_range": {"min": 99, "max": 299},
            "target_buyer": "新房业主",
            "delivery_method": "微信语音",
        },
        "content_direction": "分享装修避坑经验",
        "platform_recommendations": [
            {"platform": "抖音", "priority": 1},
            {"platform": "小红书", "priority": 2},
        ],
        "startup_materials": {
            "抖音": {
                "content_calendar": [
                    {"day": 1, "theme": "发布"},
                    {"day": 2, "theme": "互动"},
                ],
            },
        },
    }

    summary = handler._build_kit_summary(kit)
    assert "装修避坑指南" in summary
    assert "抖音" in summary
    assert "2天" in summary


@pytest.mark.asyncio
async def test_stage_two_handler_saves_messages(db):
    from starting_point.stages.stage_two import StageTwoHandler
    from starting_point.db.repos import MessageRepo, StateRepo, KitRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "试试这样改标题..."

    handler = StageTwoHandler(llm, msg_repo, state_repo, kit_repo)
    await handler.handle("u1", "这条内容怎么改更好")

    messages = await msg_repo.load("u1", stage=2)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
