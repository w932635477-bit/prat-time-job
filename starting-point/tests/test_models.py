from starting_point.models import (
    StepOption, Step, SkillStepResult,
    UserState, SkillType, ConfidenceLevel,
)


def test_step_option_creation():
    option = StepOption(label="建材/装修", value="construction")
    assert option.label == "建材/装修"
    assert option.value == "construction"


def test_step_has_options_and_free_text():
    step = Step(
        id="industry",
        question="你在哪个行业干了多少年？",
        options=[
            StepOption(label="建材/装修", value="construction"),
            StepOption(label="餐饮/食品", value="food"),
        ],
        allow_free_text=True,
    )
    assert step.id == "industry"
    assert len(step.options) == 2
    assert step.allow_free_text is True


def test_skill_step_result_stores_answer():
    result = SkillStepResult(
        step_id="industry",
        answer="建材行业12年",
        selected_option=None,
        free_text="建材行业12年",
    )
    assert result.step_id == "industry"
    assert result.free_text == "建材行业12年"


def test_user_state_tracks_current_skill():
    state = UserState(user_id="test-user")
    assert state.current_skill == SkillType.ASSESSMENT
    assert state.completed_steps == []


def test_confidence_level_values():
    assert ConfidenceLevel.LOW == "low"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.HIGH == "high"
