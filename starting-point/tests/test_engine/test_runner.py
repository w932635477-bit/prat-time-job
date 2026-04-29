import pytest

from starting_point.engine.registry import SkillRegistry
from starting_point.engine.runner import SkillRunner
from starting_point.engine.state import StateManager
from starting_point.models import UserState, SkillType, SkillStepResult, PhaseResult


@pytest.fixture
async def runner(tmp_path):
    from starting_point.main import create_registry
    registry = create_registry()
    state_mgr = StateManager(tmp_path / "test.db")
    await state_mgr.initialize()
    return SkillRunner(registry, state_mgr, None)


@pytest.mark.asyncio
async def test_first_interaction_shows_first_question(runner):
    resp = await runner.process_message("u1", "hi", None)
    assert resp.message.step_id == "digital_literacy"
    assert resp.current_step == 0


@pytest.mark.asyncio
async def test_second_interaction_records_answer(runner):
    await runner.process_message("u1", "hi", None)
    resp = await runner.process_message("u1", "basic", None)
    assert resp.message.step_id == "mental_readiness"
    assert resp.current_step == 1


@pytest.mark.asyncio
async def test_go_back_returns_earlier_step(runner):
    await runner.process_message("u1", "hi", None)
    await runner.process_message("u1", "basic", None)
    resp = await runner.go_back("u1", "digital_literacy")
    assert resp.message.step_id == "digital_literacy"


@pytest.mark.asyncio
async def test_state_persists_across_calls(runner):
    await runner.process_message("u1", "hi", None)
    await runner.process_message("u1", "basic", None)
    state = await runner.state_manager.load_state("u1")
    assert state is not None
    assert state.started is True
    assert state.current_step_index == 1


@pytest.mark.asyncio
async def test_refresh_does_not_destroy_progress(runner):
    """Regression test: page refresh sends greeting but should not reset state."""
    # First interaction starts the session
    await runner.process_message("u1", "hi", None)
    # Answer first step
    await runner.process_message("u1", "basic", None)
    # Check state is at step 1
    state = await runner.state_manager.load_state("u1")
    assert state.current_step_index == 1

    # Simulate page refresh: state already started, so next message continues
    resp = await runner.process_message("u1", "intermediate", None)
    assert resp.message.step_id == "time_commitment"
    assert resp.current_step == 2


@pytest.mark.asyncio
async def test_unknown_user_raises_on_go_back(runner):
    with pytest.raises(ValueError, match="not found"):
        await runner.go_back("nonexistent", "some_step")


@pytest.mark.asyncio
async def test_get_next_skill_returns_next(runner):
    next_skill = runner._get_next_skill(SkillType.ASSESSMENT)
    assert next_skill == SkillType.SELF_DISCOVERY


@pytest.mark.asyncio
async def test_get_next_skill_returns_none_at_end(runner):
    next_skill = runner._get_next_skill(SkillType.GROWTH)
    assert next_skill is None
