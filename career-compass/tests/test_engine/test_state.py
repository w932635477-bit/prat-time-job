import pytest
from career_compass.engine.state import StateManager
from career_compass.models import UserState, SkillStepResult, SkillType


@pytest.fixture
def state_manager(tmp_path):
    return StateManager(tmp_path / "test.db")


@pytest.mark.asyncio
async def test_create_and_load_state(state_manager):
    await state_manager.initialize()
    state = UserState(user_id="user1")
    await state_manager.save_state(state)
    loaded = await state_manager.load_state("user1")
    assert loaded is not None
    assert loaded.user_id == "user1"
    assert loaded.current_skill == SkillType.SELF_DISCOVERY


@pytest.mark.asyncio
async def test_update_step_results(state_manager):
    await state_manager.initialize()
    state = UserState(user_id="user2")
    state.step_results.append(
        SkillStepResult(step_id="industry", answer="建材行业12年"),
    )
    state.current_step_index = 1
    await state_manager.save_state(state)
    loaded = await state_manager.load_state("user2")
    assert len(loaded.step_results) == 1
    assert loaded.step_results[0].answer == "建材行业12年"


@pytest.mark.asyncio
async def test_load_nonexistent_returns_none(state_manager):
    await state_manager.initialize()
    result = await state_manager.load_state("nobody")
    assert result is None
