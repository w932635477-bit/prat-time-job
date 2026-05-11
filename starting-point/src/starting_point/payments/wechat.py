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


def _is_mobile(ua: str) -> bool:
    mobile_keywords = ["Android", "iPhone", "iPad", "iPod", "Mobile"]
    return any(kw in ua for kw in mobile_keywords)


def detect_trade_type(user_agent: str) -> str:
    if "MicroMessenger" in user_agent:
        return "JSAPI"
    if _is_mobile(user_agent):
        return "MWEB"
    return "NATIVE"


async def create_prepay_order(
    order_id: str,
    amount_fen: int,
    description: str,
    notify_url: str,
    user_agent: str = "",
    openid: str = "",
    client_ip: str = "127.0.0.1",
) -> dict:
    trade_type = detect_trade_type(user_agent)

    params = {
        "appid": settings.wx_app_id,
        "mch_id": settings.wx_pay_mch_id,
        "nonce_str": uuid.uuid4().hex[:16],
        "body": description[:128],
        "out_trade_no": order_id,
        "total_fee": str(amount_fen),
        "spbill_create_ip": client_ip,
        "notify_url": notify_url,
        "trade_type": trade_type,
    }

    if trade_type == "JSAPI" and openid:
        params["openid"] = openid

    if trade_type == "MWEB":
        params["scene_info"] = '{"h5_info":{"type":"Wap","wap_url":"https://firesing.cn","wap_name":"启点"}}'

    params["sign"] = _generate_sign(params, settings.wx_pay_api_key)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            content=_to_xml(params),
            headers={"Content-Type": "application/xml"},
        )
    data = _parse_xml(resp.text)

    if data.get("return_code") != "SUCCESS" or data.get("result_code") != "SUCCESS":
        return {"success": False, "trade_type": trade_type, "error": data.get("return_msg", "Unknown error")}

    if trade_type == "JSAPI":
        return _build_jsapi_params(data.get("prepay_id", ""))
    if trade_type == "MWEB":
        return {
            "success": True,
            "trade_type": "MWEB",
            "mweb_url": data.get("mweb_url", ""),
        }
    return {
        "success": True,
        "trade_type": "NATIVE",
        "code_url": data.get("code_url", ""),
    }


def _build_jsapi_params(prepay_id: str) -> dict:
    params = {
        "appId": settings.wx_app_id,
        "timeStamp": str(int(__import__("time").time())),
        "nonceStr": uuid.uuid4().hex[:16],
        "package": f"prepay_id={prepay_id}",
        "signType": "MD5",
    }
    params["paySign"] = _generate_sign(params, settings.wx_pay_api_key)
    return {
        "success": True,
        "trade_type": "JSAPI",
        **params,
    }


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
