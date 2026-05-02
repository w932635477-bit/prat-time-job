from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_stage_one_presents_knowledge_points(db):
    """Stage 1 starts by presenting knowledge points from Stage 0."""
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "我发现了这些可变现的知识点，你最感兴趣的是哪个？"

    # Pre-save Stage 0 results
    kps = [
        {"id": "kp_1", "description": "建材价格", "industry": "建材",
         "knowledge_type": "price_transparency", "target_buyer": "业主",
         "estimated_value": "省5000元"},
        {"id": "kp_2", "description": "渠道信息", "industry": "建材",
         "knowledge_type": "channel_info", "target_buyer": "装修人",
         "estimated_value": "省时间"},
        {"id": "kp_3", "description": "避坑经验", "industry": "建材",
         "knowledge_type": "pitfall_guide", "target_buyer": "新手",
         "estimated_value": "避免损失"},
    ]
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": kps,
    })

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="开始包装")
    assert not result.is_complete
    assert result.stage == 1


@pytest.mark.asyncio
async def test_stage_one_completes_with_valid_package(db):
    """Stage 1 completes when LLM outputs valid ProductPackage JSON."""
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()

    kps = [
        {"id": "kp_1", "description": "建材价格", "industry": "建材",
         "knowledge_type": "price_transparency", "target_buyer": "业主",
         "estimated_value": "省5000元"},
    ]
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": kps,
    })

    pkg_json = json.dumps({
        "selected_knowledge_id": "kp_1",
        "product_name": "装修材料省钱咨询",
        "one_liner": "10年建材老兵帮你审材料清单",
        "target_buyer": "正在装修预算紧张的业主",
        "service_type": "consultation",
        "price_range": {"min": 49, "max": 199, "currency": "CNY"},
        "delivery_method": "微信语音文字咨询24小时内回复",
    })
    llm.chat.return_value = f"```json\n{pkg_json}\n```"

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="我选第一个")
    assert result.is_complete
    assert result.stage == 2
