from __future__ import annotations

from starting_point.auth.jwt import decode_token
from starting_point.db.user_repo import UserRepo
from starting_point.models import User


async def get_current_user(token: str, repo: UserRepo) -> User | None:
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return await repo.get_user(user_id)
