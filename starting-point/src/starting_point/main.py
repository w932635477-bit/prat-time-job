from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from starting_point.config import settings
from starting_point.db.database import Database
from starting_point.db.migrations import run_migrations
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.llm.client import LLMClient
from starting_point.models import ChatRequest, ChatResponse
from starting_point.stages.engine import ConversationEngine

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


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

    app.state.engine = ConversationEngine(llm, msg_repo, state_repo, kit_repo)
    app.state.db = db
    app.state.llm = llm
    app.state.user_repo = user_repo
    app.state.order_repo = order_repo
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

# Route registration
from starting_point.auth.routes import router as auth_router
from starting_point.payments.routes import router as payment_router
from starting_point.user.routes import router as user_router
from starting_point.admin.routes import router as admin_router

app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(user_router)
app.include_router(admin_router)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    engine: ConversationEngine = request.app.state.engine
    from starting_point.admin.events import track_event
    await track_event(request.app.state.db, req.user_id, "chat_message")
    return await engine.handle(user_id=req.user_id, message=req.message)


@app.get("/api/kit/{user_id}")
async def get_kit(user_id: str, request: Request):
    db: Database = request.app.state.db
    kit_repo = KitRepo(db)
    kit = await kit_repo.load_by_user(user_id)
    if kit is None:
        raise HTTPException(status_code=404, detail="Kit not found")
    return kit


@app.get("/api/kit-status/{user_id}")
async def kit_status(user_id: str, request: Request):
    db: Database = request.app.state.db
    kit_repo = KitRepo(db)
    kit = await kit_repo.load_by_user(user_id)
    if kit is None:
        return {"status": "not_found"}
    return {"status": kit["generation_status"]}


@app.get("/api/state/{user_id}")
async def get_state(user_id: str, request: Request):
    db: Database = request.app.state.db
    state_repo = StateRepo(db)
    state = await state_repo.load(user_id)
    if state is None:
        return {"current_stage": None}
    return state


@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
