from __future__ import annotations

import secrets
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from starting_point.auth.jwt import create_token
from starting_point.auth.middleware import extract_bearer, get_current_user
from starting_point.auth.wechat import build_authorize_url, exchange_code_for_token, get_user_info
from starting_point.config import settings
from starting_point.db.user_repo import UserRepo
from starting_point.admin.events import track_event
from starting_point.models import User
from starting_point.wechat.token import generate_jsapi_signature, get_jsapi_ticket

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory store for QR login tokens: token -> {"user_id": str, "confirmed": bool}
_qr_login_tokens: dict[str, dict] = {}

QR_LOGIN_PREFIX = "QR_"
QR_LOGIN_EXPIRY = 300  # 5 minutes


def _get_repo(request: Request) -> UserRepo:
    return request.app.state.user_repo


def _is_wechat_browser(ua: str) -> bool:
    return "MicroMessenger" in ua


def _is_mobile(ua: str) -> bool:
    mobile_keywords = ["Android", "iPhone", "iPad", "iPod", "Mobile"]
    return any(kw in ua for kw in mobile_keywords)


@router.get("/login-info")
async def login_info(request: Request):
    ua = request.headers.get("user-agent", "")
    if _is_wechat_browser(ua):
        return {"method": "oauth", "description": "微信公众号网页授权"}
    if _is_mobile(ua):
        return {"method": "oauth_redirect", "description": "重定向到微信授权"}
    return {"method": "qrcode", "description": "扫码登录"}


@router.get("/wechat/login")
async def wechat_login(request: Request):
    state = uuid.uuid4().hex[:16]
    callback_url = str(request.base_url).rstrip("/") + "/api/auth/wechat/callback"
    url = build_authorize_url(callback_url, state=state)
    response = RedirectResponse(url)
    response.set_cookie("oauth_state", state, max_age=300, httponly=True, samesite="lax")
    return response


@router.get("/wechat/callback")
async def wechat_callback(code: str | None = None, state: str | None = None, request: Request = None):
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")

    # QR-initiated login: state starts with QR_
    if state.startswith(QR_LOGIN_PREFIX):
        return await _handle_qr_callback(code, state, request)

    # Normal OAuth login (in-WeChat browser)
    saved_state = request.cookies.get("oauth_state", "")
    if not saved_state or state != saved_state:
        raise HTTPException(400, "Invalid OAuth state")

    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(400, "Failed to exchange code for token")

    openid = token_data["openid"]
    access_token = token_data["access_token"]

    repo = _get_repo(request)
    user = await _find_or_create_user(repo, openid, access_token, token_data, request)

    jwt_token = create_token(user.id)
    await track_event(request.app.state.db, user.id, "login")
    response = RedirectResponse(url=f"/?auth=1&uid={user.id}")
    response.delete_cookie("session", path="/")
    response.set_cookie(
        "session",
        jwt_token,
        httponly=True,
        max_age=settings.jwt_expiry_hours * 3600,
        samesite="lax",
        path="/",
    )
    response.delete_cookie("oauth_state")
    return response


async def _handle_qr_callback(code: str, state: str, request: Request):
    """Handle OAuth callback from QR code scan: store result for PC polling."""
    qr_token = state[len(QR_LOGIN_PREFIX):]

    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise HTMLResponse(
            "<html><body style='text-align:center;padding-top:40vh;font-family:sans-serif'>"
            "<h2>登录失败</h2><p>请返回电脑重新扫码</p></body></html>",
            status_code=400,
        )

    openid = token_data["openid"]
    access_token = token_data["access_token"]

    repo = _get_repo(request)
    user = await _find_or_create_user(repo, openid, access_token, token_data, request)

    await track_event(request.app.state.db, user.id, "login_qrcode")

    # Store for PC polling
    _qr_login_tokens[qr_token] = {
        "user_id": user.id,
        "confirmed": True,
        "created_at": time.time(),
    }

    # Show success page in WeChat browser
    return HTMLResponse(
        "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        "<body style='text-align:center;padding-top:35vh;font-family:-apple-system,sans-serif'>"
        "<h2 style='color:#07c160'>登录成功</h2>"
        "<p style='color:#666'>请回到电脑继续操作</p>"
        "</body></html>"
    )


async def _find_or_create_user(
    repo: UserRepo, openid: str, access_token: str, token_data: dict, request: Request
) -> User:
    user = await repo.get_user_by_openid(openid)
    if user is not None:
        return user

    wx_info = await get_user_info(access_token, openid)
    nickname = wx_info.get("nickname", "") if wx_info else ""
    avatar = wx_info.get("headimgurl", "") if wx_info else ""

    # Try to link to existing anonymous user
    anon_user_id = None
    session_token = request.cookies.get("session")
    if session_token:
        from starting_point.auth.jwt import decode_token
        payload = decode_token(session_token)
        if payload:
            anon_user_id = payload.get("sub")

    if anon_user_id:
        existing = await repo.get_user(anon_user_id)
        if existing and not existing.wx_openid:
            user = User(
                id=existing.id,
                wx_openid=openid,
                wx_unionid=token_data.get("unionid", ""),
                nickname=nickname or existing.nickname,
                avatar_url=avatar or existing.avatar_url,
                tier=existing.tier,
                tier_expires_at=existing.tier_expires_at,
            )
            await repo.save_user(user)
            return user

    user = User(
        id=f"u_{uuid.uuid4().hex[:12]}",
        wx_openid=openid,
        wx_unionid=token_data.get("unionid", ""),
        nickname=nickname,
        avatar_url=avatar,
    )
    await repo.save_user(user)
    return user


# ---- QR Login (OAuth-based) ----

@router.get("/qr-login/init")
async def qr_login_init(request: Request):
    """Generate OAuth URL encoded as QR code for PC login."""
    import urllib.parse

    token = secrets.token_urlsafe(24)
    state = f"{QR_LOGIN_PREFIX}{token}"
    base = str(request.base_url).rstrip("/") if request else "https://firesing.cn"
    callback_url = base + "/api/auth/wechat/callback"
    oauth_url = build_authorize_url(callback_url, state=state)

    # Clean up expired tokens
    now = time.time()
    expired = [k for k, v in _qr_login_tokens.items() if now - v.get("created_at", 0) > QR_LOGIN_EXPIRY]
    for k in expired:
        _qr_login_tokens.pop(k, None)

    # Store pending token
    _qr_login_tokens[token] = {"user_id": "", "confirmed": False, "created_at": now}

    qr_image_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=200x200&data={urllib.parse.quote(oauth_url, safe='')}"
    )

    return {
        "token": token,
        "qr_url": qr_image_url,
        "oauth_url": oauth_url,
        "expires_in": QR_LOGIN_EXPIRY,
    }


@router.get("/qr-login/status")
async def qr_login_status(token: str):
    """Poll QR login status from PC."""
    entry = _qr_login_tokens.get(token)
    if entry is None:
        return {"status": "expired"}
    if entry.get("confirmed") and entry.get("user_id"):
        return {"status": "confirmed", "user_id": entry["user_id"]}
    return {"status": "waiting"}


# ---- Legacy QR code endpoints (kept for backward compat) ----

@router.get("/wechat/qrcode")
async def wechat_qrcode():
    return await qr_login_init(request=None)


@router.get("/wechat/qrcode-status")
async def wechat_qrcode_status(scene_id: str, request: Request):
    return await qr_login_status(token=scene_id)


# ---- JSAPI & User ----

@router.get("/wechat/jsapi-config")
async def wechat_jsapi_config(url: str):
    ticket = await get_jsapi_ticket()
    config = generate_jsapi_signature(ticket, url)
    return config


@router.get("/me")
async def get_me(request: Request):
    token = request.cookies.get("session") or extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    repo = _get_repo(request)
    user = await get_current_user(token, repo)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user.model_dump()
