import pytest
from httpx import AsyncClient, ASGITransport

from starting_point.main import app, create_registry
from starting_point.engine.state import StateManager
from starting_point.engine.runner import SkillRunner


@pytest.fixture
async def client(tmp_path):
    registry = create_registry()
    state_mgr = StateManager(tmp_path / "test.db")
    await state_mgr.initialize()
    app.state.runner = SkillRunner(registry, state_mgr, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_full_chat_flow(client):
    # Start conversation
    resp = await client.post("/api/chat", json={
        "user_id": "int-test",
        "message": "开始",
        "selected_option": None,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["step_id"] == "digital_literacy"

    # Answer first assessment question
    resp = await client.post("/api/chat", json={
        "user_id": "int-test",
        "message": "还行",
        "selected_option": None,
    })
    data = resp.json()
    assert data["message"]["step_id"] == "mental_readiness"

    # Go back
    resp = await client.post("/api/back/int-test/digital_literacy")
    data = resp.json()
    assert data["message"]["step_id"] == "digital_literacy"


@pytest.mark.asyncio
async def test_get_state(client):
    resp = await client.get("/api/state/int-test")
    assert resp.status_code == 200
