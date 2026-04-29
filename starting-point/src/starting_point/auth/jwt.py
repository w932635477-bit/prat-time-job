from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

from starting_point.config import settings

_DEV_SECRET = "dev-secret-change-in-prod"


def _validate_secret() -> None:
    secret = settings.jwt_secret
    if secret == _DEV_SECRET and settings.host != "127.0.0.1":
        raise ValueError(
            "SP_JWT_SECRET must be set to a strong secret in production. "
            "The default dev secret is only allowed on localhost."
        )
    if len(secret.encode()) < 32:
        raise ValueError(
            f"SP_JWT_SECRET must be at least 32 bytes, got {len(secret.encode())}."
        )


def create_token(user_id: str) -> str:
    _validate_secret()
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
