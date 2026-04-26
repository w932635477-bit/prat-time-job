from career_compass.skills.self_discovery import SelfDiscoverySkill
from career_compass.models import UserState


def test_skill_has_8_steps():
    skill = SelfDiscoverySkill()
    assert skill.total_steps == 8


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
