from __future__ import annotations

import hashlib
import logging
import time
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Response

from starting_point.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat", tags=["wechat-webhook"])

_login_scans: dict[str, dict] = {}


def _check_signature(signature: str, timestamp: str, nonce: str) -> bool:
    items = sorted([settings.wx_webhook_token, timestamp, nonce])
    joined = "".join(items)
    expected = hashlib.sha1(joined.encode()).hexdigest()
    return signature == expected


def _parse_xml(body: str) -> dict:
    try:
        root = ET.fromstring(body)
        return {child.tag: child.text or "" for child in root}
    except ET.ParseError:
        return {}


@router.get("/webhook")
async def verify_webhook(signature: str, timestamp: str, nonce: str, echostr: str):
    if not _check_signature(signature, timestamp, nonce):
        return Response(content="Invalid signature", status_code=403)
    return Response(content=echostr, media_type="text/plain")


@router.post("/webhook")
async def handle_webhook(request: Request):
    body = (await request.body()).decode()
    query = request.query_params
    signature = query.get("signature", "")
    timestamp = query.get("timestamp", "")
    nonce = query.get("nonce", "")

    if not _check_signature(signature, timestamp, nonce):
        return Response(content="Invalid signature", status_code=403)

    data = _parse_xml(body)
    msg_type = data.get("MsgType", "")
    event = data.get("Event", "")
    from_user = data.get("FromUserName", "")

    if msg_type == "event" and event in ("SCAN", "subscribe"):
        event_key = data.get("EventKey", "")
        scene_id = event_key.replace("qrscene_", "") if event == "subscribe" else event_key

        if scene_id and from_user:
            _login_scans[scene_id] = {
                "openid": from_user,
                "scanned_at": time.time(),
                "confirmed": True,
            }

    return Response(content="success", media_type="text/plain")


def get_scan_status(scene_id: str) -> dict | None:
    return _login_scans.get(scene_id)


def pop_scan(scene_id: str) -> dict | None:
    return _login_scans.pop(scene_id, None)
