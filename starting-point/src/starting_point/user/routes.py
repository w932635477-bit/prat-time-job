from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from starting_point.auth.middleware import get_current_user
from starting_point.db.user_repo import UserRepo

router = APIRouter(prefix="/api/user", tags=["user"])


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _get_token(request: Request) -> str:
    token = request.cookies.get("token") or _extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return token


async def _get_user(request: Request) -> object:
    token = _get_token(request)
    user_repo: UserRepo = request.app.state.user_repo
    user = await get_current_user(token, user_repo)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user


@router.get("/profile")
async def get_profile(request: Request):
    user = await _get_user(request)
    return user.model_dump()


@router.put("/profile")
async def update_profile(request: Request):
    user = await _get_user(request)
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
    user = await _get_user(request)
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
    user = await _get_user(request)
    user_repo: UserRepo = request.app.state.user_repo
    await user_repo.delete_user(user.id)
    return {"deleted": True}
