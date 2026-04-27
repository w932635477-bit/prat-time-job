import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.models import User


@pytest.fixture
async def repo(tmp_path):
    db_path = tmp_path / "test.db"
    async with aiosqlite.connect(db_path) as db:
        await run_migrations(db)
        yield UserRepo(db)


@pytest.mark.asyncio
async def test_create_and_get_user(repo):
    user = User(id="u1", wx_openid="wx123", nickname="测试用户")
    await repo.save_user(user)
    loaded = await repo.get_user("u1")
    assert loaded is not None
    assert loaded.wx_openid == "wx123"
    assert loaded.nickname == "测试用户"


@pytest.mark.asyncio
async def test_get_user_by_openid(repo):
    user = User(id="u1", wx_openid="wx123")
    await repo.save_user(user)
    loaded = await repo.get_user_by_openid("wx123")
    assert loaded is not None
    assert loaded.id == "u1"


@pytest.mark.asyncio
async def test_get_nonexistent_user(repo):
    assert await repo.get_user("nonexistent") is None
    assert await repo.get_user_by_openid("nonexistent") is None


@pytest.mark.asyncio
async def test_update_user_tier(repo):
    user = User(id="u1", wx_openid="wx123")
    await repo.save_user(user)
    updated = user.model_copy(update={"tier": "standard"})
    await repo.save_user(updated)
    loaded = await repo.get_user("u1")
    assert loaded.tier == "standard"
