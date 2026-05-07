from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from starting_point.admin.auth import verify_admin_password, verify_admin_token
from starting_point.admin.events import get_conversion_funnel
from starting_point.admin.repo import (
    get_dashboard_stats,
    get_recent_messages,
    get_feedback_list,
    get_retention_data,
)
from starting_point.db.database import Database
from starting_point.db.order_repo import OrderRepo
from starting_point.db.user_repo import UserRepo

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    password: str


def _require_admin(request: Request) -> None:
    token = request.cookies.get("admin_token") or (
        request.headers.get("authorization", "").removeprefix("Bearer ")
        if request.headers.get("authorization", "").startswith("Bearer ")
        else ""
    )
    if not token or not verify_admin_token(token):
        raise HTTPException(401, "Admin authentication required")


def _db(request: Request) -> Database:
    return request.app.state.db


@router.post("/login")
async def admin_login(body: AdminLoginRequest, request: Request):
    if not verify_admin_password(body.password):
        raise HTTPException(401, "Invalid password")
    from starting_point.admin.auth import create_admin_token
    token = create_admin_token()
    return {"token": token}


@router.get("/dashboard")
async def dashboard(request: Request):
    _require_admin(request)
    stats = await get_dashboard_stats(_db(request))
    return stats


@router.get("/users")
async def list_users(page: int = 1, size: int = 20, search: str = "", request: Request = None):
    _require_admin(request)
    user_repo: UserRepo = request.app.state.user_repo
    users = await user_repo.list_users(page, size, search)
    total = await user_repo.count_users()
    return {"total": total, "page": page, "size": size, "items": [u.model_dump() for u in users]}


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str, request: Request):
    _require_admin(request)
    user_repo: UserRepo = request.app.state.user_repo
    user = await user_repo.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    order_repo: OrderRepo = request.app.state.order_repo
    orders = await order_repo.get_orders_by_user(user_id)

    return {"user": user.model_dump(), "orders": [o.model_dump() for o in orders]}


@router.get("/orders")
async def list_orders(page: int = 1, size: int = 20, status: str = "", request: Request = None):
    _require_admin(request)
    order_repo: OrderRepo = request.app.state.order_repo
    orders = await order_repo.list_orders(page, size, status)
    total = await order_repo.count_orders(status)
    return {"total": total, "page": page, "size": size, "items": [o.model_dump() for o in orders]}


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, request: Request):
    _require_admin(request)
    order_repo: OrderRepo = request.app.state.order_repo
    order = await order_repo.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order.model_dump()


@router.get("/analytics/revenue")
async def revenue_analytics(days: int = 30, request: Request = None):
    _require_admin(request)
    order_repo: OrderRepo = request.app.state.order_repo
    daily = await order_repo.revenue_by_day(days)
    total = await order_repo.total_revenue()
    return {"total_revenue": total, "daily": daily}


@router.get("/analytics/conversion")
async def conversion_funnel(request: Request):
    _require_admin(request)
    return await get_conversion_funnel(_db(request))


@router.get("/analytics/retention")
async def retention_analytics(request: Request):
    _require_admin(request)
    return await get_retention_data(_db(request))


@router.get("/messages/recent")
async def recent_messages(limit: int = 50, request: Request = None):
    _require_admin(request)
    return await get_recent_messages(_db(request), limit)


@router.get("/feedback")
async def feedback_list(page: int = 1, size: int = 20, request: Request = None):
    _require_admin(request)
    return await get_feedback_list(_db(request), page, size)
