import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations
from starting_point.db.order_repo import OrderRepo
from starting_point.models import Order


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_pay.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_create_order(db):
    repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=2900)
    await repo.save_order(order)
    loaded = await repo.get_order("o1")
    assert loaded is not None
    assert loaded.tier == "standard"
    assert loaded.amount == 2900


@pytest.mark.asyncio
async def test_update_order_status(db):
    repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=2900)
    await repo.save_order(order)
    await repo.update_status("o1", "paid", wx_transaction_id="wx_tx_123")
    loaded = await repo.get_order("o1")
    assert loaded.status == "paid"
    assert loaded.wx_transaction_id == "wx_tx_123"


@pytest.mark.asyncio
async def test_get_orders_by_user(db):
    repo = OrderRepo(db)
    await repo.save_order(Order(id="o1", user_id="u1", tier="standard", amount=2900))
    await repo.save_order(Order(id="o2", user_id="u1", tier="human", amount=19900))
    orders = await repo.get_orders_by_user("u1")
    assert len(orders) == 2


@pytest.mark.asyncio
async def test_human_tier_order(db):
    repo = OrderRepo(db)
    order = Order(id="o3", user_id="u1", tier="human", amount=19900)
    await repo.save_order(order)
    loaded = await repo.get_order("o3")
    assert loaded.tier == "human"
    assert loaded.amount == 19900
