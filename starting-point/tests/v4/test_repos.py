from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_save_and_load_messages(db):
    from starting_point.db.repos import MessageRepo

    repo = MessageRepo(db)
    await repo.save(user_id="u1", role="user", content="你好", stage=0)
    await repo.save(user_id="u1", role="assistant", content="你做什么行业的？", stage=0)
    messages = await repo.load(user_id="u1", stage=0)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_count_user_messages(db):
    from starting_point.db.repos import MessageRepo

    repo = MessageRepo(db)
    await repo.save(user_id="u1", role="user", content="hi", stage=0)
    await repo.save(user_id="u1", role="assistant", content="hello", stage=0)
    await repo.save(user_id="u1", role="user", content="hi again", stage=0)
    count = await repo.count_by_role(user_id="u1", stage=0, role="user")
    assert count == 2


@pytest.mark.asyncio
async def test_save_and_load_state(db):
    from starting_point.db.repos import StateRepo

    repo = StateRepo(db)
    await repo.save(user_id="u1", current_stage=0, stage_data={"count": 3})
    state = await repo.load(user_id="u1")
    assert state is not None
    assert state["current_stage"] == 0
    assert state["stage_data"]["count"] == 3


@pytest.mark.asyncio
async def test_update_state(db):
    from starting_point.db.repos import StateRepo

    repo = StateRepo(db)
    await repo.save(user_id="u1", current_stage=0, stage_data={"count": 1})
    await repo.save(user_id="u1", current_stage=1, stage_data={"count": 5})
    state = await repo.load(user_id="u1")
    assert state["current_stage"] == 1


@pytest.mark.asyncio
async def test_save_and_load_kit(db):
    from starting_point.db.repos import KitRepo

    repo = KitRepo(db)
    kit_id = await repo.create(user_id="u1", knowledge_points=[{"id": "kp_1"}])
    assert kit_id is not None
    kit = await repo.load_by_user(user_id="u1")
    assert kit is not None
    assert kit["generation_status"] == "pending"


@pytest.mark.asyncio
async def test_update_kit_status(db):
    from starting_point.db.repos import KitRepo

    repo = KitRepo(db)
    kit_id = await repo.create(user_id="u1")
    await repo.update_status(kit_id=kit_id, status="completed")
    kit = await repo.load_by_user(user_id="u1")
    assert kit["generation_status"] == "completed"
