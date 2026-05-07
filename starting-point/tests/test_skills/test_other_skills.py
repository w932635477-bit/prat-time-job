import json
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
    assert "14" in prompt
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
    assert "task_plan" in updates
    assert updates["task_plan"].total_days >= 1


def test_market_radar_prompt_contains_industry():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_market_radar_prompt(
        industry="建材", assets="瓷砖选购经验", market_signals="有人主动咨询",
    )
    assert "建材" in prompt
    assert "闲鱼" in prompt
    assert "existing_sellers" in prompt


def test_task_day_model_defaults():
    from starting_point.models import TaskDay
    td = TaskDay(day=1, task="发帖子", platform="小红书")
    assert td.status == "active"
    assert td.stuck_reason is None
    assert td.estimated_time == ""


def test_task_plan_model():
    from starting_point.models import TaskPlan, TaskDay
    plan = TaskPlan(
        total_days=14,
        current_day=1,
        days=[TaskDay(day=1, task="测试", platform="小红书")],
        platform="小红书",
    )
    assert plan.status == "active"
    assert len(plan.days) == 1


def test_user_state_has_task_plan_field():
    from starting_point.models import UserState, TaskPlan
    state = UserState(user_id="test")
    assert state.task_plan is None
    state2 = UserState(user_id="test", task_plan=TaskPlan(total_days=20))
    assert state2.task_plan.total_days == 20


def test_stuck_rescue_prompt_contains_task_info():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_stuck_rescue_prompt(
        day=5,
        task="在小红书发一篇装修避坑笔记",
        platform="小红书",
        stuck_reason="不知道怎么拍照，手机拍出来效果很差",
        completed_days=4,
    )
    assert "小红书" in prompt
    assert "装修避坑" in prompt
    assert "拍照" in prompt
    assert "建议" in prompt or "advice" in prompt.lower()


def test_adaptive_daily_tasks_prompt_uses_suggested_days():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_daily_tasks_prompt(
        platform="小红书",
        service_name="装修避坑咨询",
        asset_map="瓷砖选购经验",
        market_signals="有人主动咨询",
        digital_literacy="intermediate",
        time_commitment="1-3h",
        suggested_days=20,
    )
    assert "20" in prompt


def test_customer_acquisition_has_daily_checkin_step():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()
    step = skill.get_step(3)
    assert step is not None
    assert step.id == "daily_checkin"


def test_customer_acquisition_total_steps_is_4():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()
    assert skill.total_steps == 4


def test_process_checkin_done_updates_plan():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, TaskPlan, TaskDay
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    state.task_plan = TaskPlan(
        total_days=3,
        current_day=1,
        days=[
            TaskDay(day=1, task="发帖", platform="小红书"),
            TaskDay(day=2, task="回复", platform="小红书"),
            TaskDay(day=3, task="优化", platform="小红书"),
        ],
        platform="小红书",
    )
    result = skill.process_answer("daily_checkin", "完成了", state)
    assert result.next_step is False
    assert result.deliverable is not None


def test_process_checkin_stuck_returns_rescue_signal():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, TaskPlan, TaskDay
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    state.task_plan = TaskPlan(
        total_days=3,
        current_day=1,
        days=[TaskDay(day=1, task="发帖", platform="小红书")],
        platform="小红书",
    )
    result = skill.process_answer("daily_checkin", "卡住了：不知道怎么拍照", state)
    assert result.confidence_boost is not None
    assert result.deliverable is not None
    assert result.deliverable.get("stuck") is True


def test_process_checkin_last_day_completes_plan():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, TaskPlan, TaskDay
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    state.task_plan = TaskPlan(
        total_days=1,
        current_day=1,
        days=[TaskDay(day=1, task="发帖", platform="小红书")],
        platform="小红书",
    )
    result = skill.process_answer("daily_checkin", "完成了", state)
    assert result.next_step is True
    plan_update = result.deliverable["task_plan_update"]
    assert plan_update["status"] == "completed"


def test_calculate_suggested_days():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()
    assert skill._calculate_suggested_days("beginner", "1h") == 28
    assert skill._calculate_suggested_days("advanced", "3-5h") == 14
    assert skill._calculate_suggested_days("intermediate", "1-3h") == 14


@pytest.mark.asyncio
async def test_customer_acquisition_generates_adaptive_plan():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    tasks = [{"day": i, "task": f"任务{i}", "platform": "小红书", "estimated_time": "30分钟", "why": "原因", "success_signal": "信号"} for i in range(1, 15)]
    llm.chat.return_value = json.dumps({"tasks": tasks})

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test")
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu", selected_option="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert "tasks" in output
    assert output["suggested_days"] == 14
    assert "task_plan" in updates
    assert updates["task_plan"].total_days == 14
    assert len(updates["task_plan"].days) == 14


@pytest.mark.asyncio
async def test_customer_acquisition_beginner_gets_more_days():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, UserAssessment, SkillStepResult

    llm = AsyncMock()
    tasks = [{"day": i, "task": f"任务{i}", "platform": "小红书", "estimated_time": "30分钟", "why": "原因", "success_signal": "信号"} for i in range(1, 22)]
    llm.chat.return_value = json.dumps({"tasks": tasks})

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test", assessment=UserAssessment(digital_literacy="beginner", time_commitment="1h"))
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert output["suggested_days"] >= 21


@pytest.mark.asyncio
async def test_rescue_generates_advice():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill

    llm = AsyncMock()
    llm.chat.return_value = '{"encouragement": "坚持到了第3天很棒", "diagnosis": "拍照技巧不够", "steps": ["用自然光", "拍3张选最好的"], "alternative": "先发文字笔记", "next_action": "完成后继续第4天"}'

    skill = CustomerAcquisitionSkill(llm_client=llm)
    result = await skill.generate_rescue(
        day=3, task="在小红书发一篇装修避坑笔记", platform="小红书",
        stuck_reason="不知道怎么拍照", completed_days=2,
    )
    assert result is not None
    assert len(result.get("steps", [])) > 0
    assert result.get("diagnosis") is not None
