import pytest

from starting_point.skills.self_discovery import SelfDiscoverySkill
from starting_point.models import UserState


def test_skill_has_11_steps():
    skill = SelfDiscoverySkill()
    assert skill.total_steps == 11


def test_first_step_is_industry():
    skill = SelfDiscoverySkill()
    step = skill.get_step(0)
    assert step.id == "industry"
    assert len(step.options) > 0


def test_process_answer_returns_next_step():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    result = skill.process_answer("industry", "建材行业", state)
    assert result.next_step is True


def test_process_negative_answer_returns_boost():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    result = skill.process_answer("proud_moment", "我不行，没什么特别的", state)
    assert result.confidence_boost is not None


def test_process_detailed_answer_returns_boost():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    result = skill.process_answer(
        "save_money_story",
        "帮客户省了3000块瓷砖钱，80块的品牌砖换成了35块的工程砖",
        state,
    )
    assert result.confidence_boost is not None
    assert result.next_step is True


def test_step_8_is_content_search():
    skill = SelfDiscoverySkill()
    step = skill.get_step(8)
    assert step.id == "content_search"
    assert step.allow_free_text is True


def test_step_9_is_organic_inquiry():
    skill = SelfDiscoverySkill()
    step = skill.get_step(9)
    assert step.id == "organic_inquiry"
    assert step.allow_free_text is True


def test_step_10_is_shared_pain():
    skill = SelfDiscoverySkill()
    step = skill.get_step(10)
    assert step.id == "shared_pain"
    assert step.allow_free_text is True


def test_extraction_prompt_mentions_market_signals():
    from starting_point.llm.prompts import PromptBuilder

    builder = PromptBuilder()
    prompt = builder.build_extraction_prompt("- industry: 建材\n- content_search: 装修避坑")
    assert "市场信号" in prompt or "market_signal" in prompt


@pytest.mark.asyncio
async def test_generate_output_includes_market_signals_when_llm_returns_them():
    from unittest.mock import AsyncMock
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    llm.chat.return_value = '{"capabilities": [], "resources": [], "confidence_level": "medium", "market_signals": {"demand_evidence": "有人问装修", "search_intent": "瓷砖选购", "shared_pain_point": "被坑", "market_readiness": "high"}}'

    skill = SelfDiscoverySkill(llm_client=llm)
    state = UserState(user_id="test")
    for step_id in ["industry", "proud_moment", "save_money_story", "insider_knowledge", "people_ask_me", "price_judgment", "unique_resources", "first_100", "content_search", "organic_inquiry", "shared_pain"]:
        state.step_results.append(SkillStepResult(step_id=step_id, answer=f"answer for {step_id}"))

    output, updates = await skill.generate_output(state)
    assert updates["asset_map"].market_signals is not None
    assert updates["asset_map"].market_signals.demand_evidence == "有人问装修"
    assert updates["asset_map"].market_signals.market_readiness == "high"


@pytest.mark.asyncio
async def test_generate_output_includes_market_radar():
    from unittest.mock import AsyncMock
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    # First call: asset extraction. Second call: market radar.
    llm.chat.side_effect = [
        '{"capabilities": [{"name": "瓷砖选购", "description": "帮客户选砖", "evidence": "20年经验", "estimated_value": "50-200元/次"}], "resources": ["渠道"], "confidence_level": "high", "market_signals": {"demand_evidence": "有人问", "search_intent": "瓷砖", "shared_pain_point": "被坑", "market_readiness": "high"}}',
        '{"existing_sellers": ["闲鱼上有人卖装修咨询"], "price_range": "50-300元", "hot_topics": ["装修避坑", "建材选购"], "unique_edge": "20年实战经验", "demand_level": "high", "summary": "建材咨询市场需求旺盛"}',
    ]

    skill = SelfDiscoverySkill(llm_client=llm)
    state = UserState(user_id="test")
    for step_id in ["industry", "proud_moment", "save_money_story", "insider_knowledge", "people_ask_me", "price_judgment", "unique_resources", "first_100", "content_search", "organic_inquiry", "shared_pain"]:
        state.step_results.append(SkillStepResult(step_id=step_id, answer=f"answer for {step_id}"))

    output, updates = await skill.generate_output(state)
    assert "market_radar" in output
    assert len(output["market_radar"].get("existing_sellers", [])) > 0
    assert llm.chat.call_count == 2
