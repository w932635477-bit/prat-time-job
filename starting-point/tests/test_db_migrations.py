import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_users_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_orders_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_user_profiles_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_user_states_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_states'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_insert_user(db):
    await db.execute(
        "INSERT INTO users (id, wx_openid, tier) VALUES (?, ?, ?)",
        ("u1", "wx123", "free"),
    )
    await db.commit()
    cursor = await db.execute("SELECT wx_openid, tier FROM users WHERE id = ?", ("u1",))
    row = await cursor.fetchone()
    assert row == ("wx123", "free")
