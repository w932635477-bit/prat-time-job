from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from starting_point.auth.middleware import get_user_from_request
from starting_point.db.user_repo import UserRepo

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile")
async def get_profile(request: Request):
    user = await get_user_from_request(request)
    return user.model_dump()


@router.put("/profile")
async def update_profile(request: Request):
    user = await get_user_from_request(request)
    body = await request.json()
    updated = user.model_copy(update={
        k: v for k, v in body.items()
        if k in ("nickname", "phone") and v is not None
    })
    user_repo: UserRepo = request.app.state.user_repo
    await user_repo.save_user(updated)
    return updated.model_dump()


@router.get("/export")
async def export_data(request: Request):
    user = await get_user_from_request(request)
    user_repo: UserRepo = request.app.state.user_repo
    from starting_point.db.order_repo import OrderRepo
    order_repo: OrderRepo = request.app.state.order_repo

    orders = await order_repo.get_orders_by_user(user.id)
    return {
        "user": user.model_dump(),
        "orders": [o.model_dump() for o in orders],
    }


@router.delete("/account")
async def delete_account(request: Request):
    user = await get_user_from_request(request)
    user_repo: UserRepo = request.app.state.user_repo
    await user_repo.delete_user(user.id)
    return {"deleted": True}
