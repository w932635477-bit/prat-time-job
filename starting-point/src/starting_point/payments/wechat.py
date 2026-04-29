from __future__ import annotations

import hashlib
import uuid

import httpx

from starting_point.config import settings


def _generate_sign(params: dict, api_key: str) -> str:
    sorted_params = sorted(params.items())
    query = "&".join(f"{k}={v}" for k, v in sorted_params if v)
    query += f"&key={api_key}"
    return hashlib.md5(query.encode()).hexdigest().upper()


async def create_prepay_order(
    order_id: str,
    amount_fen: int,
    description: str,
    openid: str,
    notify_url: str,
) -> dict:
    params = {
        "appid": settings.wx_app_id,
        "mch_id": settings.wx_pay_mch_id,
        "nonce_str": uuid.uuid4().hex[:16],
        "body": description[:128],
        "out_trade_no": order_id,
        "total_fee": str(amount_fen),
        "spbill_create_ip": "127.0.0.1",
        "notify_url": notify_url,
        "trade_type": "JSAPI",
        "openid": openid,
    }
    params["sign"] = _generate_sign(params, settings.wx_pay_api_key)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            content=_to_xml(params),
            headers={"Content-Type": "application/xml"},
        )
    return _parse_xml(resp.text)


async def verify_callback(xml_body: str, api_key: str) -> dict | None:
    data = _parse_xml(xml_body)
    if not data:
        return None
    sign = data.pop("sign", "")
    expected = _generate_sign(data, api_key)
    if sign != expected:
        return None
    return data


def _to_xml(params: dict) -> str:
    items = "".join(f"<{k}><![CDATA[{v}]]></{k}>" for k, v in params.items())
    return f"<xml>{items}</xml>"


def _parse_xml(xml: str) -> dict:
    import defusedxml.ElementTree as ET
    try:
        root = ET.fromstring(xml)
        return {child.tag: child.text or "" for child in root}
    except ET.ParseError:
        return {}
