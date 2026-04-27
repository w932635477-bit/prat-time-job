from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from starting_point.auth.middleware import get_current_user
from starting_point.config import settings
from starting_point.db.order_repo import OrderRepo
from starting_point.db.user_repo import UserRepo
from starting_point.models import Order, TIER_DEFINITIONS
from starting_point.payments.tiers import get_tiers
from starting_point.payments.wechat import create_prepay_order, verify_callback

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/tiers")
async def list_tiers():
    return get_tiers()


@router.post("/create")
async def create_order(tier: str, request: Request):
    if tier not in TIER_DEFINITIONS or tier == "free":
        raise HTTPException(400, "Invalid tier")

    token = request.cookies.get("token") or _extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")

    user_repo: UserRepo = request.app.state.user_repo
    user = await get_current_user(token, user_repo)
    if not user:
        raise HTTPException(401, "Invalid token")

    tier_def = TIER_DEFINITIONS[tier]
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        user_id=user.id,
        tier=tier,
        amount=tier_def["price_fen"],
    )

    order_repo: OrderRepo = request.app.state.order_repo
    await order_repo.save_order(order)

    notify_url = str(request.base_url).rstrip("/") + "/api/payments/wechat/callback"
    prepay = await create_prepay_order(
        order_id=order.id,
        amount_fen=tier_def["price_fen"],
        description=tier_def["label"],
        openid=user.wx_openid,
        notify_url=notify_url,
    )
    return {"order_id": order.id, "prepay": prepay}


@router.post("/wechat/callback")
async def wechat_pay_callback(request: Request):
    body = await request.body()
    data = await verify_callback(body.decode(), settings.wx_pay_api_key)
    if not data:
        return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>"

    order_repo: OrderRepo = request.app.state.order_repo
    user_repo: UserRepo = request.app.state.user_repo

    order_id = data.get("out_trade_no", "")
    order = await order_repo.get_order(order_id)
    if not order:
        return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>"

    await order_repo.update_status(
        order_id, "paid", data.get("transaction_id", ""),
    )

    tier_def = TIER_DEFINITIONS.get(order.tier, {})
    duration_days = tier_def.get("duration_days", 60) or 60
    user = await user_repo.get_user(order.user_id)
    if user:
        updated = user.model_copy(update={
            "tier": order.tier,
            "tier_expires_at": datetime.now() + timedelta(days=duration_days),
        })
        await user_repo.save_user(updated)

    return "<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>"


@router.get("/status/{order_id}")
async def payment_status(order_id: str, request: Request):
    order_repo: OrderRepo = request.app.state.order_repo
    order = await order_repo.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": order.status, "tier": order.tier}


@router.get("/orders")
async def list_user_orders(user_id: str, request: Request):
    order_repo: OrderRepo = request.app.state.order_repo
    orders = await order_repo.get_orders_by_user(user_id)
    return [o.model_dump() for o in orders]


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
