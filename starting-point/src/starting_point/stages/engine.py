from __future__ import annotations

import logging

from starting_point.llm.client import LLMClient
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.models import ChatResponse
from starting_point.stages.stage_zero import StageZeroHandler
from starting_point.stages.stage_one import StageOneHandler
from starting_point.stages.kit_generator import KitGenerator

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Routes user messages to the correct stage handler based on state."""

    def __init__(
        self,
        llm: LLMClient,
        msg_repo: MessageRepo,
        state_repo: StateRepo,
        kit_repo: KitRepo,
    ) -> None:
        self._llm = llm
        self._msg_repo = msg_repo
        self._state_repo = state_repo
        self._kit_repo = kit_repo

    async def handle(self, user_id: str, message: str) -> ChatResponse:
        state = await self._state_repo.load(user_id)
        current_stage = state["current_stage"] if state else 0

        if current_stage == 0:
            handler = StageZeroHandler(self._llm, self._msg_repo, self._state_repo)
            result = await handler.handle(user_id, message)
            if result.is_complete:
                return result
            return result

        if current_stage == 1:
            handler = StageOneHandler(self._llm, self._msg_repo, self._state_repo)
            result = await handler.handle(user_id, message)
            if result.is_complete:
                # Stage 1 complete, trigger kit generation
                try:
                    kit_gen = KitGenerator(self._llm, self._kit_repo)
                    kps = result.stage_data.get("knowledge_points", [])
                    pkg = result.stage_data.get("product_package", {})
                    kit = await kit_gen.generate(user_id, kps, pkg)
                    result = ChatResponse(
                        message=result.message,
                        stage=result.stage,
                        stage_data={**result.stage_data, "kit_id": kit["id"]},
                        is_complete=result.is_complete,
                    )
                except Exception as e:
                    logger.error("Kit generation failed: %s", e)
                    result = ChatResponse(
                        message=result.message,
                        stage=result.stage,
                        stage_data={**result.stage_data, "kit_error": "启动套件生成失败，请重试"},
                        is_complete=result.is_complete,
                    )
            return result

        # Stage 2+ = kit generated, user is viewing results
        return ChatResponse(
            message="你的启动套件已经生成完毕！",
            stage=2,
            stage_data=state["stage_data"] if state else {},
            is_complete=False,
        )
