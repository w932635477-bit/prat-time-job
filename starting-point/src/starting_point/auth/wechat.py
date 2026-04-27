from __future__ import annotations

import secrets
import urllib.parse

import httpx

from starting_point.config import settings


def build_authorize_url(redirect_uri: str) -> str:
    state = secrets.token_urlsafe(16)
    params = {
        "appid": settings.wx_app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": state,
    }
    return f"https://open.weixin.qq.com/connect/oauth2/authorize?{urllib.parse.urlencode(params)}#wechat_redirect"


def parse_callback_code(params: dict) -> str | None:
    return params.get("code")


async def exchange_code_for_token(code: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wx_app_id,
                "secret": settings.wx_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        return None
    data = resp.json()
    if "openid" not in data:
        return None
    return data


async def get_user_info(access_token: str, openid: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
        )
    if resp.status_code != 200:
        return None
    return resp.json()
