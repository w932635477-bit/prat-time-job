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
async def test_stage_one_includes_stage_zero_context(db):
    """Stage 1 system prompt includes Stage 0 conversation summary."""
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()
    llm.chat.return_value = "你在建材行业干了15年，太厉害了。你最值钱的是价格透明度。"

    # Simulate Stage 0 conversation history
    await msg_repo.save("u1", "assistant", "你在建材行业做了多久？", stage=0)
    await msg_repo.save("u1", "user", "我做了15年建材，主要做瓷砖和卫浴", stage=0)
    await msg_repo.save("u1", "assistant", "你了解渠道价格吗？", stage=0)
    await msg_repo.save("u1", "user", "当然，出厂价到零售价差3倍以上", stage=0)

    kps = [
        {"id": "kp_1", "description": "建材价格", "industry": "建材",
         "knowledge_type": "price_transparency", "target_buyer": "业主",
         "estimated_value": "省5000元"},
    ]
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": kps,
    })

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="好，帮我包装")

    assert not result.is_complete
    # Verify the LLM was called with a system prompt containing Stage 0 context
    call_args = llm.chat.call_args
    system_prompt = call_args.kwargs.get("system", "")
    assert "15年建材" in system_prompt
    assert "出厂价" in system_prompt


@pytest.mark.asyncio
async def test_stage_one_no_completion_before_min_messages(db):
    """Stage 1 should not extract before MIN_STAGE1_MESSAGES."""
    from starting_point.stages.stage_one import MIN_STAGE1_MESSAGES
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
        "user_message_count": MIN_STAGE1_MESSAGES - 1,
    })

    # Even if LLM returns valid JSON, should not complete before min
    pkg_json = json.dumps({
        "selected_knowledge_id": "kp_1",
        "product_name": "装修材料省钱咨询",
        "one_liner": "10年建材老兵帮你审材料清单",
        "target_buyer": "正在装修预算紧张的业主",
        "service_type": "consultation",
        "price_range": {"min": 49, "max": 199, "currency": "CNY"},
        "delivery_method": "微信语音文字咨询24小时内回复",
    })
    llm.chat.return_value = f"好的，让我帮你定一个方案。\n```json\n{pkg_json}\n```"

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="我选第一个")

    assert not result.is_complete


@pytest.mark.asyncio
async def test_stage_one_completes_at_max_messages(db):
    """Stage 1 force-extracts at MAX_STAGE1_MESSAGES."""
    from starting_point.stages.stage_one import MAX_STAGE1_MESSAGES
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo
    from starting_point.models import ProductPackage, PriceRange

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
        "user_message_count": MAX_STAGE1_MESSAGES - 1,
    })

    pkg = ProductPackage(
        selected_knowledge_id="kp_1",
        product_name="装修材料省钱咨询",
        one_liner="10年建材老兵帮你审材料清单",
        target_buyer="正在装修预算紧张的业主",
        service_type="consultation",
        price_range=PriceRange(min=49, max=199),
        delivery_method="微信语音文字咨询24小时内回复",
    )
    llm.chat_json.return_value = pkg

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="我选第一个")

    assert result.is_complete
    assert result.stage == 2


@pytest.mark.asyncio
async def test_stage_one_force_complete_uses_all_kps(db):
    """Force completion uses all knowledge points, not just the first."""
    from starting_point.stages.stage_one import MAX_STAGE1_MESSAGES
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo

    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    llm = AsyncMock()

    kps = [
        {"id": "kp_1", "description": "建材价格透明", "industry": "建材",
         "knowledge_type": "price_transparency", "target_buyer": "业主",
         "estimated_value": "省5000元"},
        {"id": "kp_2", "description": "渠道信息", "industry": "建材",
         "knowledge_type": "channel_info", "target_buyer": "装修人",
         "estimated_value": "省时间"},
    ]
    await state_repo.save("u1", 1, {
        "status": "completed",
        "knowledge_points": kps,
        "user_message_count": MAX_STAGE1_MESSAGES - 1,
    })

    # Make chat_json fail to trigger force_complete
    llm.chat.return_value = "not valid json"
    llm.chat_json.side_effect = ValueError("extraction failed")

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="就这个吧")

    assert result.is_complete
    assert "建材" in result.message
    assert result.stage_data.get("force_completed") is True


@pytest.mark.asyncio
async def test_stage_one_early_extraction_on_plan_summary(db):
    """Stage 1 extracts early when LLM produces a complete product plan."""
    from starting_point.stages.stage_one import MIN_STAGE1_MESSAGES
    from starting_point.stages.stage_one import StageOneHandler
    from starting_point.db.repos import MessageRepo, StateRepo
    from starting_point.models import ProductPackage, PriceRange

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
        "user_message_count": MIN_STAGE1_MESSAGES + 2,
    })

    # LLM returns a plan summary (triggers _has_plan_summary)
    llm.chat.return_value = (
        "好，方案就这么定了。\n\n"
        "**产品名称：** 建材砍价咨询\n"
        "**定价：** 99-199元\n"
        "**交付方式：** 微信一对一咨询"
    )

    # chat_json returns a valid ProductPackage
    pkg = ProductPackage(
        selected_knowledge_id="kp_1",
        product_name="建材砍价咨询",
        one_liner="帮你砍到出厂价",
        target_buyer="预算紧张的装修业主",
        service_type="consultation",
        price_range=PriceRange(min=99, max=199),
        delivery_method="微信一对一咨询45分钟",
    )
    llm.chat_json.return_value = pkg

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="就这样吧")

    assert result.is_complete
    assert result.stage == 2
    assert "建材砍价咨询" in result.message


@pytest.mark.asyncio
async def test_stage_one_no_early_extraction_without_plan(db):
    """Stage 1 does not extract early when LLM is still gathering info."""
    from starting_point.stages.stage_one import MIN_STAGE1_MESSAGES
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
        "user_message_count": MIN_STAGE1_MESSAGES + 1,
    })

    # LLM asks a follow-up question (no plan summary)
    llm.chat.return_value = "你打算收多少钱？99元还是199元？"

    handler = StageOneHandler(llm, msg_repo, state_repo)
    result = await handler.handle(user_id="u1", message="我还没想好")

    assert not result.is_complete


@pytest.mark.asyncio
async def test_summarize_stage_zero_extracts_user_statements():
    """_summarize_stage_zero extracts key user statements."""
    from starting_point.stages.stage_one import StageOneHandler

    handler = StageOneHandler.__new__(StageOneHandler)
    history = [
        {"role": "assistant", "content": "你在建材行业做了多久？", "stage": 0},
        {"role": "user", "content": "我做了15年建材，主要做瓷砖和卫浴", "stage": 0},
        {"role": "assistant", "content": "你了解渠道价格吗？", "stage": 0},
        {"role": "user", "content": "出厂价到零售价差3倍以上", "stage": 0},
    ]

    summary = handler._summarize_stage_zero(history)
    assert "15年建材" in summary
    assert "出厂价" in summary
    assert "渠道价格" in summary


@pytest.mark.asyncio
async def test_summarize_stage_zero_empty():
    """_summarize_stage_zero returns empty string for no history."""
    from starting_point.stages.stage_one import StageOneHandler

    handler = StageOneHandler.__new__(StageOneHandler)
    assert handler._summarize_stage_zero([]) == ""
    assert handler._summarize_stage_zero([{"role": "assistant", "content": "hi", "stage": 0}]) == ""
