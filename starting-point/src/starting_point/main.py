from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from starting_point.config import settings
from starting_point.db.database import Database
from starting_point.db.migrations import run_migrations
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.db.creator_repo import CreatorRepo
from starting_point.engine.registry import SkillRegistry
from starting_point.llm.client import LLMClient
from starting_point.models import ChatRequest, ChatResponse, SkillType
from starting_point.stages.engine import ConversationEngine
from starting_point.skills.assessment import AssessmentSkill
from starting_point.skills.self_discovery import SelfDiscoverySkill
from starting_point.skills.product_packaging import ProductPackagingSkill
from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
from starting_point.skills.first_deal import FirstDealSkill
from starting_point.skills.growth import GrowthSkill
from starting_point.skills.plan_path import PlanPathSkill
from starting_point.skills.take_action import TakeActionSkill
from starting_point.skills.troubleshoot import TroubleshootSkill

STATIC_DIR = (
    settings.static_dir
    if str(settings.static_dir)
    else Path(__file__).resolve().parent.parent.parent / "static"
)


def create_registry() -> SkillRegistry:
    """Create a SkillRegistry with all skill classes registered."""
    registry = SkillRegistry()
    registry.register(SkillType.ASSESSMENT, AssessmentSkill())
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill())
    registry.register(SkillType.PRODUCT_PACKAGING, ProductPackagingSkill())
    registry.register(SkillType.CUSTOMER_ACQUISITION, CustomerAcquisitionSkill())
    registry.register(SkillType.FIRST_DEAL, FirstDealSkill())
    registry.register(SkillType.GROWTH, GrowthSkill())
    registry.register(SkillType.PLAN_PATH, PlanPathSkill())
    registry.register(SkillType.TROUBLESHOOT, TroubleshootSkill())
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(settings.database_path)
    await db.initialize()
    await run_migrations(db)

    llm = LLMClient()
    msg_repo = MessageRepo(db)
    state_repo = StateRepo(db)
    kit_repo = KitRepo(db)
    user_repo = UserRepo(db)
    order_repo = OrderRepo(db)
    creator_repo = CreatorRepo(db.conn())

    app.state.engine = ConversationEngine(
        llm, msg_repo, state_repo, kit_repo, creator_repo,
    )
    app.state.db = db
    app.state.llm = llm
    app.state.user_repo = user_repo
    app.state.order_repo = order_repo
    app.state.creator_repo = creator_repo
    yield
    await llm.close()
    await db.close()


app = FastAPI(
    title="启点 v4.0",
    description="帮助中年失业者发现经验价值、包装产品、生成启动套件",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# In-memory rate limiter: sliding window per client IP
_RATE_LIMITS: dict[str, list[float]] = defaultdict(list)
_RATE_MAX_REQUESTS = 120
_RATE_WINDOW_SECONDS = 60

# Stricter limits for sensitive endpoints
_STRICT_PATHS = {"/api/auth/login", "/api/auth/wechat/callback", "/api/payments/create", "/api/admin/login"}
_STRICT_MAX_REQUESTS = 10


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        now = time.monotonic()

        max_req = _STRICT_MAX_REQUESTS if path in _STRICT_PATHS else _RATE_MAX_REQUESTS
        window = _RATE_WINDOW_SECONDS

        key = f"{client_ip}:{path}" if path in _STRICT_PATHS else client_ip
        timestamps = _RATE_LIMITS[key]

        # Prune entries outside the window
        _RATE_LIMITS[key] = [t for t in timestamps if now - t < window]
        timestamps = _RATE_LIMITS[key]

        if len(timestamps) >= max_req:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
            )

        _RATE_LIMITS[key].append(now)
        response = await call_next(request)
        return response


app.add_middleware(RateLimitMiddleware)

# Route registration
from starting_point.auth.routes import router as auth_router
from starting_point.payments.routes import router as payment_router
from starting_point.user.routes import router as user_router
from starting_point.admin.routes import router as admin_router
from starting_point.wechat.webhook import router as wechat_webhook_router

app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(wechat_webhook_router)


# ---- Session auth ----

class SessionRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


def _get_session_user_id(request: Request) -> str:
    """Verify JWT session cookie and return authenticated user_id."""
    from starting_point.auth.jwt import decode_token
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="No session")
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return payload.get("sub", "")


@app.post("/api/session")
async def create_session(req: SessionRequest, request: Request, response: JSONResponse):
    """Issue a JWT session cookie for a user_id. Called once on first visit."""
    from starting_point.auth.jwt import create_token
    token = create_token(req.user_id)

    user_repo: UserRepo = request.app.state.user_repo
    existing = await user_repo.get_user(req.user_id)
    if existing is None:
        conn = request.app.state.db.conn()
        await conn.execute(
            "INSERT OR IGNORE INTO users (id, wx_openid, tier, created_at, updated_at) "
            "VALUES (?, NULL, 'free', datetime('now'), datetime('now'))",
            (req.user_id,),
        )
        await conn.commit()

    resp = JSONResponse({"ok": True, "user_id": req.user_id})
    resp.delete_cookie("session", path="/")
    resp.set_cookie(
        "session",
        token,
        httponly=True,
        max_age=settings.jwt_expiry_hours * 3600,
        samesite="lax",
        path="/",
    )
    return resp


@app.get("/api/session")
async def check_session(request: Request):
    """Check if current session is valid. Returns user_id and tier if authenticated."""
    try:
        user_id = _get_session_user_id(request)
        user_repo: UserRepo = request.app.state.user_repo
        user = await user_repo.get_user(user_id)
        tier = user.tier if user else "free"
        return {"authenticated": True, "user_id": user_id, "tier": tier}
    except HTTPException:
        return {"authenticated": False, "user_id": None, "tier": "free"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    session_user_id = _get_session_user_id(request)
    if session_user_id != req.user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    engine: ConversationEngine = request.app.state.engine
    from starting_point.admin.events import track_event
    await track_event(request.app.state.db, req.user_id, "chat_message")

    user_repo: UserRepo = request.app.state.user_repo
    user = await user_repo.get_user(req.user_id)
    tier = user.tier if user else "free"
    tier_expires_at = user.tier_expires_at if user else None

    result = await engine.handle(
        user_id=req.user_id,
        message=req.message,
        tier=tier,
        tier_expires_at=tier_expires_at,
    )
    return result


@app.get("/api/kit/{user_id}")
async def get_kit(user_id: str, request: Request):
    session_user_id = _get_session_user_id(request)
    if session_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db: Database = request.app.state.db
    kit_repo = KitRepo(db)
    kit = await kit_repo.load_by_user(user_id)
    if kit is None:
        raise HTTPException(status_code=404, detail="Kit not found")
    return kit


@app.get("/api/kit-status/{user_id}")
async def kit_status(user_id: str, request: Request):
    session_user_id = _get_session_user_id(request)
    if session_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db: Database = request.app.state.db
    kit_repo = KitRepo(db)
    kit = await kit_repo.load_by_user(user_id)
    if kit is None:
        return {"status": "not_found"}
    return {"status": kit["generation_status"]}


@app.get("/api/state/{user_id}")
async def get_state(user_id: str, request: Request):
    session_user_id = _get_session_user_id(request)
    if session_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db: Database = request.app.state.db
    state_repo = StateRepo(db)
    state = await state_repo.load(user_id)
    if state is None:
        return {"current_stage": None}
    return state


class CheckinRequest(BaseModel):
    kit_id: str = Field(...)
    platform: str = Field(...)
    day: int = Field(..., ge=1, le=7)


@app.post("/api/checkin")
async def create_checkin(req: CheckinRequest, request: Request):
    user_id = _get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    db: Database = request.app.state.db
    cursor = await db.conn().execute(
        "INSERT OR IGNORE INTO checkins (user_id, kit_id, platform, day) VALUES (?, ?, ?, ?)",
        (user_id, req.kit_id, req.platform, req.day),
    )
    await db.conn().commit()
    return {"ok": True, "new": cursor.rowcount > 0}


@app.get("/api/checkins/{user_id}")
async def get_checkins(user_id: str, request: Request):
    session_user_id = _get_session_user_id(request)
    if session_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db: Database = request.app.state.db
    cursor = await db.conn().execute(
        "SELECT kit_id, platform, day FROM checkins WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return {"checkins": [{"kit_id": r[0], "platform": r[1], "day": r[2]} for r in rows]}


@app.get("/api/messages/{user_id}")
async def get_messages(user_id: str, request: Request, stage: int = -1):
    session_user_id = _get_session_user_id(request)
    if session_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db: Database = request.app.state.db
    msg_repo = MessageRepo(db)
    if stage < 0:
        state_repo = StateRepo(db)
        state = await state_repo.load(user_id)
        stage = state["current_stage"] if state else 0
    messages = await msg_repo.load(user_id, stage)
    return {"messages": messages, "stage": stage}


@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
