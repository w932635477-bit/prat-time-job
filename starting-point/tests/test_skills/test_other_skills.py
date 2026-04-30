import pytest

from starting_point.skills.plan_path import PlanPathSkill
from starting_point.skills.take_action import TakeActionSkill
from starting_point.skills.troubleshoot import TroubleshootSkill
from starting_point.models import UserState


def test_plan_path_has_6_steps():
    skill = PlanPathSkill()
    assert skill.total_steps == 6


def test_plan_path_first_step_is_urgency():
    skill = PlanPathSkill()
    step = skill.get_step(0)
    assert step.id == "urgency"
    assert len(step.options) >= 2


def test_plan_path_process_answer():
    skill = PlanPathSkill()
    state = UserState(user_id="test")
    result = skill.process_answer("urgency", "几天内见到钱", state)
    assert result.next_step is True


def test_take_action_has_2_steps():
    skill = TakeActionSkill()
    assert skill.total_steps == 2


def test_take_action_first_step_is_platform():
    skill = TakeActionSkill()
    step = skill.get_step(0)
    assert step.id == "platform"


def test_troubleshoot_has_1_step():
    skill = TroubleshootSkill()
    assert skill.total_steps == 1


def test_troubleshoot_step_is_problem_type():
    skill = TroubleshootSkill()
    step = skill.get_step(0)
    assert step.id == "problem_type"
    assert len(step.options) == 4


def test_daily_tasks_prompt_contains_key_fields():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_daily_tasks_prompt(
        platform="小红书",
        service_name="装修避坑咨询",
        asset_map="瓷砖选购经验",
        market_signals="有人主动咨询",
        digital_literacy="intermediate",
        time_commitment="1-3h",
    )
    assert "小红书" in prompt
    assert "7" in prompt
    assert "任务" in prompt or "task" in prompt.lower()


@pytest.mark.asyncio
async def test_customer_acquisition_generates_daily_tasks():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    llm.chat.return_value = '{"tasks": [{"day": 1, "task": "发帖子", "platform": "小红书", "estimated_time": "20分钟", "why": "原因", "success_signal": "有人问"}]}'

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test")
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu", selected_option="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert "tasks" in output
    assert len(output["tasks"]) >= 1


def test_market_radar_prompt_contains_industry():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_market_radar_prompt(
        industry="建材", assets="瓷砖选购经验", market_signals="有人主动咨询",
    )
    assert "建材" in prompt
    assert "闲鱼" in prompt
    assert "existing_sellers" in prompt
