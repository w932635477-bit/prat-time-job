from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from starting_point.llm.client import LLMClient
from starting_point.db.repos import MessageRepo, StateRepo
from starting_point.models import ProductPackage, ChatResponse, NextStep
from starting_point.prompts.stage_one import SYSTEM_PROMPT
from starting_point.utils.json import extract_json

logger = logging.getLogger(__name__)


class StageOneHandler:
    """Stage 1 product packaging handler.

    Presents knowledge points from Stage 0 and guides the user
    through defining a product package.
    """

    def __init__(
        self,
        llm: LLMClient,
        msg_repo: MessageRepo,
        state_repo: StateRepo,
    ) -> None:
        self._llm = llm
        self._msg_repo = msg_repo
        self._state_repo = state_repo

    async def handle(self, user_id: str, message: str, creator_context: str = "") -> ChatResponse:
        await self._msg_repo.save(user_id, "user", message, stage=1)

        state = await self._state_repo.load(user_id)
        stage_data = state["stage_data"] if state else {}
        kps = stage_data.get("knowledge_points", [])

        # Build context with knowledge points
        kp_context = f"已识别的可变现知识点:\n{json.dumps(kps, ensure_ascii=False, indent=2)}\n\n"
        system_prompt = SYSTEM_PROMPT + kp_context
        if creator_context:
            system_prompt += creator_context

        history = await self._msg_repo.load(user_id, stage=1)
        llm_messages = [{"role": h["role"], "content": h["content"]} for h in history]

        response_text = await self._llm.chat(
            messages=llm_messages,
            system=system_prompt,
        )

        parsed = extract_json(response_text)
        if parsed and "product_name" in parsed:
            try:
                validated = ProductPackage.model_validate(parsed)
                new_stage_data = {
                    **stage_data,
                    "product_package": validated.model_dump(),
                }
                await self._msg_repo.save(user_id, "assistant", response_text, stage=1)
                await self._state_repo.save(user_id, 2, new_stage_data)

                return ChatResponse(
                    message=response_text,
                    stage=2,
                    stage_data=new_stage_data,
                    is_complete=True,
                    next_step=NextStep(
                        title="生成你的启动套件",
                        description="你的产品已经包装完成！下一步是生成完整的启动套件 — 包含话术模板、发布计划和行动清单。",
                        auto_prompt="生成我的启动套件",
                    ),
                )
            except ValidationError:
                logger.warning("Stage 1 product package validation failed")

        await self._msg_repo.save(user_id, "assistant", response_text, stage=1)
        await self._state_repo.save(user_id, 1, stage_data)

        return ChatResponse(
            message=response_text,
            stage=1,
            stage_data=stage_data,
            is_complete=False,
        )
