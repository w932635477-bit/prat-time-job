from career_compass.skills.plan_path import PlanPathSkill
from career_compass.skills.take_action import TakeActionSkill
from career_compass.skills.troubleshoot import TroubleshootSkill
from career_compass.models import UserState


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
