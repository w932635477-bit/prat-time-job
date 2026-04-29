import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport

from starting_point.main import app, create_registry
from starting_point.auth.jwt import create_token
from starting_point.auth.middleware import get_user_from_request
from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.engine.state import StateManager
from starting_point.engine.runner import SkillRunner
from starting_point.models import User


@pytest.fixture
async def app_with_db(tmp_path):
    db_path = tmp_path / "test.db"
    registry = create_registry()
    state_mgr = StateManager(db_path)
    await state_mgr.initialize()
    app.state.runner = SkillRunner(registry, state_mgr, None)

    db_conn = await aiosqlite.connect(db_path)
    await run_migrations(db_conn)
    app.state.user_repo = UserRepo(db_conn)
    app.state.order_repo = OrderRepo(db_conn)
    yield db_conn
    await db_conn.close()


@pytest.mark.asyncio
async def test_chat_without_token_returns_401(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/chat", json={"user_id": "u1", "message": "hi"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_with_valid_token(app_with_db):
    user = User(id="u1", wx_openid="wx_test", nickname="Test")
    await app.state.user_repo.save_user(user)
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/api/chat",
            json={"user_id": "u1", "message": "hi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_state_wrong_user_returns_403(app_with_db):
    user = User(id="u1", wx_openid="wx_test", nickname="Test")
    await app.state.user_repo.save_user(user)
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/state/u_other",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_state_own_user_returns_200(app_with_db):
    user = User(id="u1", wx_openid="wx_test", nickname="Test")
    await app.state.user_repo.save_user(user)
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/state/u1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_payment_status_requires_auth(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/payments/status/ord_123")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_payment_orders_requires_auth(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/payments/orders")
        assert resp.status_code == 401
