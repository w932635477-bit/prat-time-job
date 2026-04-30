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


def test_asset_map_has_market_signals_field():
    from starting_point.models import AssetMap, MarketSignals
    signals = MarketSignals(
        demand_evidence="有人咨询",
        search_intent="装修避坑",
        shared_pain_point="瓷砖被坑",
        market_readiness="high",
    )
    am = AssetMap(market_signals=signals)
    assert am.market_signals.demand_evidence == "有人咨询"
    assert am.market_signals.market_readiness == "high"


def test_asset_map_market_signals_default_none():
    from starting_point.models import AssetMap
    am = AssetMap()
    assert am.market_signals is None


def test_daily_task_creation():
    from starting_point.models import DailyTask
    task = DailyTask(
        day=1, task="在闲鱼发一条咨询帖子", platform="闲鱼",
        estimated_time="20分钟", why="你上次说的瓷砖经验正是业主需要的",
        success_signal="有人来问",
    )
    assert task.day == 1
    assert task.platform == "闲鱼"


def test_daily_task_plan_creation():
    from starting_point.models import DailyTask, DailyTaskPlan
    tasks = [DailyTask(day=1, task="test", platform="x", estimated_time="10分钟", why="reason", success_signal="sig")]
    plan = DailyTaskPlan(tasks=tasks, platform="小红书")
    assert len(plan.tasks) == 1
    assert plan.platform == "小红书"
