from __future__ import annotations

import hashlib
import hmac

from starting_point.auth.jwt import create_token, decode_token
from starting_point.config import settings


def verify_admin_password(password: str) -> bool:
    return hmac.compare_digest(password, settings.admin_password)


def create_admin_token() -> str:
    return create_token("admin")


def verify_admin_token(token: str) -> bool:
    payload = decode_token(token)
    if payload is None:
        return False
    return payload.get("sub") == "admin"
