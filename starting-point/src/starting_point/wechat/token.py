from __future__ import annotations

import hashlib
import time
import uuid

import httpx

from starting_point.config import settings

_access_token_cache: dict[str, str | float] = {}
_jsapi_ticket_cache: dict[str, str | float] = {}


async def get_access_token() -> str:
    cached_token = _access_token_cache.get("token")
    cached_expiry = _access_token_cache.get("expires_at", 0)
    if cached_token and time.time() < cached_expiry:
        return cached_token

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": settings.wx_app_id,
                "secret": settings.wx_app_secret,
            },
        )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Failed to get access_token: {data}")

    token = data["access_token"]
    expires_in = data.get("expires_in", 7200)
    _access_token_cache["token"] = token
    _access_token_cache["expires_at"] = time.time() + expires_in - 300
    return token


async def get_jsapi_ticket() -> str:
    cached_ticket = _jsapi_ticket_cache.get("ticket")
    cached_expiry = _jsapi_ticket_cache.get("expires_at", 0)
    if cached_ticket and time.time() < cached_expiry:
        return cached_ticket

    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/ticket/getticket",
            params={"access_token": token, "type": "jsapi"},
        )
    data = resp.json()
    if data.get("errcode", 0) != 0:
        raise RuntimeError(f"Failed to get jsapi_ticket: {data}")

    ticket = data["ticket"]
    expires_in = data.get("expires_in", 7200)
    _jsapi_ticket_cache["ticket"] = ticket
    _jsapi_ticket_cache["expires_at"] = time.time() + expires_in - 300
    return ticket


def generate_jsapi_signature(ticket: str, url: str) -> dict:
    nonce_str = uuid.uuid4().hex[:16]
    timestamp = str(int(time.time()))
    params = f"jsapi_ticket={ticket}&noncestr={nonce_str}&timestamp={timestamp}&url={url}"
    signature = hashlib.sha1(params.encode()).hexdigest()
    return {
        "appId": settings.wx_app_id,
        "timestamp": timestamp,
        "nonceStr": nonce_str,
        "signature": signature,
    }
