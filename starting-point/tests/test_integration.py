import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport

from starting_point.main import app, create_registry
from starting_point.engine.state import StateManager
from starting_point.engine.runner import SkillRunner
from starting_point.auth.jwt import create_token
from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.models import User


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
    registry = create_registry()
    state_mgr = StateManager(db_path)
    await state_mgr.initialize()
    app.state.runner = SkillRunner(registry, state_mgr, None)

    db_conn = await aiosqlite.connect(db_path)
    await run_migrations(db_conn)
    app.state.user_repo = UserRepo(db_conn)
    app.state.order_repo = OrderRepo(db_conn)

    user = User(id="int-test-user", wx_openid="wx_test", nickname="Test")
    await app.state.user_repo.save_user(user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await db_conn.close()


@pytest.fixture
def auth_headers():
    token = create_token("int-test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_chat_flow(client, auth_headers):
    resp = await client.post("/api/chat", json={
        "user_id": "int-test-user",
        "message": "开始",
        "selected_option": None,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["step_id"] == "digital_literacy"

    resp = await client.post("/api/chat", json={
        "user_id": "int-test-user",
        "message": "还行",
        "selected_option": None,
    }, headers=auth_headers)
    data = resp.json()
    assert data["message"]["step_id"] == "mental_readiness"

    resp = await client.post("/api/back/int-test-user/digital_literacy", headers=auth_headers)
    data = resp.json()
    assert data["message"]["step_id"] == "digital_literacy"


@pytest.mark.asyncio
async def test_get_state(client, auth_headers):
    resp = await client.get("/api/state/int-test-user", headers=auth_headers)
    assert resp.status_code == 200
