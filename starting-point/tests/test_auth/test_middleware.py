import pytest
from httpx import AsyncClient, ASGITransport

from starting_point.main import app
from starting_point.auth.jwt import create_token
from starting_point.config import settings
from starting_point.db.database import Database
from starting_point.db.migrations import run_migrations
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.llm.client import LLMClient
from starting_point.models import User
from starting_point.stages.engine import ConversationEngine


@pytest.fixture
async def app_with_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    await db.initialize()
    await run_migrations(db)

    llm = LLMClient()
    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    user_repo = UserRepo(db)
    order_repo = OrderRepo(db)

    app.state.db = db
    app.state.engine = ConversationEngine(llm, msg_repo, state_repo, kit_repo)
    app.state.user_repo = user_repo
    app.state.order_repo = order_repo
    yield db
    await llm.close()
    await db.close()


@pytest.mark.asyncio
async def test_chat_without_session_returns_401(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/chat", json={"user_id": "u1", "message": "hi"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_wrong_user_returns_403(app_with_db):
    token = create_token("u1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/api/chat",
            json={"user_id": "u_other", "message": "hi"},
            cookies={"session": token},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_state_without_session_returns_401(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/state/u1")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_state_wrong_user_returns_403(app_with_db):
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/state/u_other",
            cookies={"session": token},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_state_own_user_returns_200(app_with_db):
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/state/u1",
            cookies={"session": token},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_messages_without_session_returns_401(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/messages/u1")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_session_endpoint_sets_cookie(app_with_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/api/session",
            json={"user_id": "u_test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["user_id"] == "u_test"


@pytest.mark.asyncio
async def test_check_session_returns_user_id(app_with_db):
    token = create_token("u1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/session",
            cookies={"session": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "u1"
