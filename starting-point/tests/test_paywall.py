from datetime import datetime, timedelta
from starting_point.payments.access import check_phase_access


def test_free_user_phase0_allowed():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=0)
    assert result.allowed is True


def test_free_user_phase1_allowed():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=1)
    assert result.allowed is True


def test_free_user_phase2_blocked():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=2)
    assert result.allowed is False


def test_standard_user_phase5_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="standard", tier_expires_at=expiry, phase_index=5)
    assert result.allowed is True


def test_expired_standard_blocked():
    expiry = datetime.now() - timedelta(days=1)
    result = check_phase_access(tier="standard", tier_expires_at=expiry, phase_index=2)
    assert result.allowed is False


def test_low_ticket_phase2_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="low_ticket", tier_expires_at=expiry, phase_index=2)
    assert result.allowed is True


def test_low_ticket_phase3_blocked():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="low_ticket", tier_expires_at=expiry, phase_index=3)
    assert result.allowed is False


def test_human_all_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="human", tier_expires_at=expiry, phase_index=5)
    assert result.allowed is True
