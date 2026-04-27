from starting_point.models import User, Order, UserProfile, TIER_DEFINITIONS


def test_user_defaults():
    u = User(id="u1", wx_openid="wx123")
    assert u.tier == "free"
    assert u.tier_expires_at is None
    assert u.nickname == ""


def test_order_defaults():
    o = Order(id="o1", user_id="u1", tier="standard", amount=5900)
    assert o.status == "pending"
    assert o.paid_at is None


def test_tier_definitions():
    assert TIER_DEFINITIONS["free"]["price_fen"] == 0
    assert TIER_DEFINITIONS["standard"]["price_fen"] == 5900
    assert TIER_DEFINITIONS["low_ticket"]["duration_days"] == 60
