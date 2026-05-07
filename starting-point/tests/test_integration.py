import pytest
from httpx import AsyncClient, ASGITransport

from starting_point.main import app
from starting_point.auth.jwt import create_token
from starting_point.db.database import Database
from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.engine.state import StateManager
from starting_point.engine.runner import SkillRunner
from starting_point.models import User, SkillType


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    await db.initialize()
    await run_migrations(db)

    app.state.db = db
    app.state.user_repo = UserRepo(db)
    app.state.order_repo = OrderRepo(db)

    user = User(id="int-test-user", wx_openid="wx_test", nickname="Test")
    await app.state.user_repo.save_user(user)

    token = create_token("int-test-user")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("session", token)
        yield c

    await db.close()


@pytest.mark.asyncio
async def test_get_state(client):
    resp = await client.get("/api/state/int-test-user")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_state_wrong_user_returns_403(client):
    resp = await client.get("/api/state/u_other")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_full_self_discovery_with_market_signals(tmp_path):
    """Regression test: 11 steps complete and advance to next skill."""
    from starting_point.main import create_registry

    db_path = tmp_path / "test.db"
    registry = create_registry()
    state_mgr = StateManager(db_path)
    await state_mgr.initialize()
    runner = SkillRunner(registry, state_mgr, None)

    # Complete assessment (4 steps)
    await runner.process_message("u1", "hi", None)
    for answer in ["basic", "ready", "1-3h", "moderate"]:
        await runner.process_message("u1", answer, None)

    # Complete self_discovery (11 steps)
    for step_id in [
        "industry",
        "proud_moment",
        "save_money_story",
        "insider_knowledge",
        "people_ask_me",
        "price_judgment",
        "unique_resources",
        "first_100",
        "content_search",
        "organic_inquiry",
        "shared_pain",
    ]:
        await runner.process_message("u1", f"test answer for {step_id}", None)

    # After self_discovery completes, should advance to next skill
    state = await state_mgr.load_state("u1")
    assert state.current_skill != SkillType.SELF_DISCOVERY
