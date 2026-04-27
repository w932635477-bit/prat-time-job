from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AccessResult:
    allowed: bool
    reason: str = ""


def check_phase_access(
    tier: str,
    tier_expires_at: datetime | None,
    phase_index: int,
) -> AccessResult:
    if phase_index <= 1:
        return AccessResult(allowed=True)

    if tier == "free":
        return AccessResult(allowed=False, reason="free_tier_limit")

    if tier_expires_at and datetime.now() > tier_expires_at:
        return AccessResult(allowed=False, reason="tier_expired")

    if tier == "low_ticket" and phase_index > 2:
        return AccessResult(allowed=False, reason="low_ticket_limit")

    if tier in ("low_ticket", "standard", "human"):
        return AccessResult(allowed=True)

    return AccessResult(allowed=False, reason="unknown_tier")
