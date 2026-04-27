from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from starting_point.auth.jwt import create_token
from starting_point.auth.middleware import get_current_user
from starting_point.auth.wechat import build_authorize_url, exchange_code_for_token, get_user_info
from starting_point.config import settings
from starting_point.db.user_repo import UserRepo
from starting_point.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_repo(request: Request) -> UserRepo:
    return request.app.state.user_repo


@router.get("/wechat/login")
async def wechat_login(request: Request):
    callback_url = str(request.base_url).rstrip("/") + "/api/auth/wechat/callback"
    url = build_authorize_url(callback_url)
    return RedirectResponse(url)


@router.get("/wechat/callback")
async def wechat_callback(code: str | None = None, state: str | None = None, request: Request = None):
    if not code:
        raise HTTPException(400, "Missing authorization code")

    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(400, "Failed to exchange code for token")

    openid = token_data["openid"]
    access_token = token_data["access_token"]

    repo = _get_repo(request)
    user = await repo.get_user_by_openid(openid)

    if user is None:
        wx_info = await get_user_info(access_token, openid)
        nickname = wx_info.get("nickname", "") if wx_info else ""
        avatar = wx_info.get("headimgurl", "") if wx_info else ""
        user = User(
            id=f"u_{uuid.uuid4().hex[:12]}",
            wx_openid=openid,
            wx_unionid=token_data.get("unionid", ""),
            nickname=nickname,
            avatar_url=avatar,
        )
        await repo.save_user(user)

    jwt_token = create_token(user.id)
    response = RedirectResponse(url="/app.html")
    response.set_cookie("token", jwt_token, httponly=True, max_age=settings.jwt_expiry_hours * 3600)
    return response


@router.get("/me")
async def get_me(request: Request):
    token = request.cookies.get("token") or _extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    repo = _get_repo(request)
    user = await get_current_user(token, repo)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user.model_dump()


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
