from __future__ import annotations

import uuid

import httpx

from starting_point.config import settings
from starting_point.wechat.token import get_access_token
from starting_point.wechat.webhook import get_scan_status, pop_scan


async def create_login_qrcode() -> dict:
    scene_id = uuid.uuid4().hex[:16]
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.weixin.qq.com/cgi-bin/qrcode/create",
            params={"access_token": token},
            json={
                "expire_seconds": 300,
                "action_name": "QR_STR_SCENE",
                "action_info": {"scene": {"scene_str": scene_id}},
            },
        )
    data = resp.json()
    if "ticket" not in data:
        raise RuntimeError(f"Failed to create QR code: {data}")

    ticket = data["ticket"]
    expire_seconds = data.get("expire_seconds", 300)
    qr_url = f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={ticket}"

    return {
        "scene_id": scene_id,
        "qr_url": qr_url,
        "expires_in": expire_seconds,
    }


def check_qr_scan(scene_id: str) -> dict:
    scan = get_scan_status(scene_id)
    if scan is None:
        return {"status": "waiting"}
    if scan.get("confirmed"):
        return {"status": "confirmed", "openid": scan["openid"]}
    return {"status": "scanned"}


def consume_qr_scan(scene_id: str) -> dict | None:
    return pop_scan(scene_id)
