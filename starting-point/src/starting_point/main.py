from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from starting_point.config import settings
from starting_point.engine.registry import SkillRegistry
from starting_point.engine.runner import SkillRunner
from starting_point.engine.state import StateManager
from starting_point.llm.client import DeepSeekClient
from starting_point.models import ChatRequest, ChatResponse, SkillType
from starting_point.skills.self_discovery import SelfDiscoverySkill
from starting_point.skills.plan_path import PlanPathSkill
from starting_point.skills.take_action import TakeActionSkill
from starting_point.skills.troubleshoot import TroubleshootSkill

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


def create_registry(llm_client: DeepSeekClient | None = None) -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill(llm_client))
    registry.register(SkillType.PLAN_PATH, PlanPathSkill(llm_client))
    registry.register(SkillType.TAKE_ACTION, TakeActionSkill(llm_client))
    registry.register(SkillType.TROUBLESHOOT, TroubleshootSkill())
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm_client = DeepSeekClient() if settings.deepseek_api_key else None
    registry = create_registry(llm_client)
    state_manager = StateManager(settings.database_path)
    await state_manager.initialize()
    app.state.runner = SkillRunner(registry, state_manager, llm_client)
    yield


app = FastAPI(
    title="Starting Point API",
    description="启点 — 帮助中年失业者将行业经验转化为收入",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    runner: SkillRunner = app.state.runner
    return await runner.process_message(
        request.user_id, request.message, request.selected_option,
    )


@app.post("/api/back/{user_id}/{step_id}", response_model=ChatResponse)
async def go_back(user_id: str, step_id: str) -> ChatResponse:
    runner: SkillRunner = app.state.runner
    return await runner.go_back(user_id, step_id)


@app.get("/api/state/{user_id}")
async def get_state(user_id: str):
    runner: SkillRunner = app.state.runner
    state = await runner.state_manager.load_state(user_id)
    if state is None:
        return {"error": "User not found"}
    return state.model_dump()


@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
