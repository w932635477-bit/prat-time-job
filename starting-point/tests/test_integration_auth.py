import pytest
import aiosqlite
from datetime import datetime, timedelta

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.models import User, Order
from starting_point.auth.jwt import create_token, decode_token
from starting_point.auth.middleware import get_current_user
from starting_point.payments.access import check_phase_access


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_integration.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_full_auth_and_payment_flow(db):
    # 1. Create user (simulates WeChat OAuth callback)
    user_repo = UserRepo(db)
    user = User(id="u1", wx_openid="wx_test", nickname="测试用户")
    await user_repo.save_user(user)

    # 2. Issue JWT
    token = create_token("u1")
    payload = decode_token(token)
    assert payload["sub"] == "u1"

    # 3. Middleware extracts user
    loaded = await get_current_user(token, user_repo)
    assert loaded.nickname == "测试用户"

    # 4. Free user can access Phase 0 and 1
    assert check_phase_access("free", None, 0).allowed is True
    assert check_phase_access("free", None, 1).allowed is True
    assert check_phase_access("free", None, 2).allowed is False

    # 5. Create order
    order_repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=2900)
    await order_repo.save_order(order)

    # 6. Simulate payment callback
    await order_repo.update_status("o1", "paid", "wx_tx_123")
    updated_order = await order_repo.get_order("o1")
    assert updated_order.status == "paid"

    # 7. Update user tier
    updated_user = user.model_copy(update={
        "tier": "standard",
        "tier_expires_at": datetime.now() + timedelta(days=60),
    })
    await user_repo.save_user(updated_user)

    # 8. Verify access
    loaded2 = await user_repo.get_user("u1")
    assert loaded2.tier == "standard"
    assert check_phase_access(loaded2.tier, loaded2.tier_expires_at, 5).allowed is True


@pytest.mark.asyncio
async def test_delete_user_cascades(db):
    user_repo = UserRepo(db)
    order_repo = OrderRepo(db)

    user = User(id="u2", wx_openid="wx_del", nickname="待删除")
    await user_repo.save_user(user)

    order = Order(id="o2", user_id="u2", tier="human", amount=19900)
    await order_repo.save_order(order)

    await user_repo.delete_user("u2")

    assert await user_repo.get_user("u2") is None
    orders = await order_repo.get_orders_by_user("u2")
    assert len(orders) == 0


@pytest.mark.asyncio
async def test_expired_tier_blocks_access(db):
    user_repo = UserRepo(db)
    user = User(
        id="u3", wx_openid="wx_exp", nickname="过期用户",
        tier="standard",
        tier_expires_at=datetime.now() - timedelta(days=1),
    )
    await user_repo.save_user(user)

    result = check_phase_access("standard", user.tier_expires_at, 3)
    assert result.allowed is False
    assert result.reason == "tier_expired"
