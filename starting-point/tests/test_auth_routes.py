import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.models import User
from starting_point.auth.jwt import create_token


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_auth.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_get_me_valid_token(db):
    repo = UserRepo(db)
    user = User(id="u1", wx_openid="wx1", nickname="测试")
    await repo.save_user(user)
    token = create_token("u1")

    from starting_point.auth.middleware import get_current_user
    result = await get_current_user(token, repo)
    assert result is not None
    assert result.id == "u1"


@pytest.mark.asyncio
async def test_get_me_invalid_token(db):
    repo = UserRepo(db)
    from starting_point.auth.middleware import get_current_user
    result = await get_current_user("invalid.token", repo)
    assert result is None


@pytest.mark.asyncio
async def test_get_me_deleted_user(db):
    repo = UserRepo(db)
    token = create_token("nonexistent")
    from starting_point.auth.middleware import get_current_user
    result = await get_current_user(token, repo)
    assert result is None
