from __future__ import annotations

from fastapi import HTTPException, Request

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


def extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def get_token(request: Request) -> str:
    token = request.cookies.get("token") or request.cookies.get("session") or extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return token


async def get_user_from_request(request: Request) -> User:
    token = get_token(request)
    user_repo: UserRepo = request.app.state.user_repo
    user = await get_current_user(token, user_repo)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user
