from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from career_compass.config import settings
from career_compass.engine.registry import SkillRegistry
from career_compass.engine.runner import SkillRunner
from career_compass.engine.state import StateManager
from career_compass.llm.client import DeepSeekClient
from career_compass.models import ChatRequest, ChatResponse, SkillType
from career_compass.skills.self_discovery import SelfDiscoverySkill
from career_compass.skills.plan_path import PlanPathSkill
from career_compass.skills.take_action import TakeActionSkill
from career_compass.skills.troubleshoot import TroubleshootSkill


def create_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill())
    registry.register(SkillType.PLAN_PATH, PlanPathSkill())
    registry.register(SkillType.TAKE_ACTION, TakeActionSkill())
    registry.register(SkillType.TROUBLESHOOT, TroubleshootSkill())
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = create_registry()
    state_manager = StateManager(settings.database_path)
    await state_manager.initialize()
    llm_client = DeepSeekClient() if settings.deepseek_api_key else None
    app.state.runner = SkillRunner(registry, state_manager, llm_client)
    yield


app = FastAPI(
    title="Career Compass API",
    description="AI变现合伙人",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
