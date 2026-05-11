from __future__ import annotations

import json
import logging

from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.models import ChatResponse
from starting_point.payments.access import check_phase_access
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
        creator_repo: object | None = None,
    ) -> None:
        self._llm = llm
        self._msg_repo = msg_repo
        self._state_repo = state_repo
        self._kit_repo = kit_repo
        self._creator_repo = creator_repo
        self._prompt_builder = PromptBuilder()

    async def handle(
        self,
        user_id: str,
        message: str,
        tier: str = "free",
        tier_expires_at=None,
    ) -> ChatResponse:
        state = await self._state_repo.load(user_id)
        current_stage = state["current_stage"] if state else 0

        access = check_phase_access(tier, tier_expires_at, current_stage)
        if not access.allowed:
            return ChatResponse(
                message="你已经完成了免费体验部分。解锁完整方案，继续你的旅程。",
                stage=current_stage,
                is_complete=False,
            )

        creator_context = await self._get_creator_context(user_id, message, state)

        if current_stage == 0:
            handler = StageZeroHandler(self._llm, self._msg_repo, self._state_repo)
            result = await handler.handle(user_id, message, creator_context)
            if result.is_complete:
                return result
            return result

        if current_stage == 1:
            handler = StageOneHandler(self._llm, self._msg_repo, self._state_repo)
            result = await handler.handle(user_id, message, creator_context)
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
                        next_step=result.next_step,
                    )
                except Exception as e:
                    logger.error("Kit generation failed: %s", e)
                    result = ChatResponse(
                        message=result.message,
                        stage=result.stage,
                        stage_data={**result.stage_data, "kit_error": "启动套件生成失败，请重试"},
                        is_complete=result.is_complete,
                        next_step=result.next_step,
                    )
            return result

        # Stage 2+ = kit generated, user is viewing results
        return ChatResponse(
            message="你的启动套件已经生成完毕！",
            stage=2,
            stage_data=state["stage_data"] if state else {},
            is_complete=False,
        )

    async def _get_creator_context(
        self,
        user_id: str,
        message: str,
        state: dict | None,
    ) -> str:
        if self._creator_repo is None:
            return ""
        keywords = self._extract_industry_keywords(message, state)
        if not keywords:
            return ""
        for keyword in keywords:
            creators = await self._creator_repo.search(keyword, limit=2)
            if creators:
                return self._prompt_builder.build_creator_context(creators)
        return ""

    def _extract_industry_keywords(
        self,
        message: str,
        state: dict | None,
    ) -> list[str]:
        keywords: list[str] = []
        if state:
            stage_data = state.get("stage_data", {})
            for kp in stage_data.get("knowledge_points", []):
                if isinstance(kp, dict) and kp.get("industry"):
                    keywords.append(kp["industry"])
        industry_hints = [
            "餐饮", "厨师", "小吃", "卤味", "烧烤", "面馆",
            "建材", "装修", "瓦工", "电工", "木工", "油漆",
            "家政", "月嫂", "保洁", "育婴", "保姆",
            "农业", "水果", "茶叶", "蜂蜜", "养殖",
            "服装", "缝纫", "摆摊", "尾货",
            "美业", "美甲", "美容", "推拿", "艾灸", "美发",
            "汽修", "二手车", "驾校", "电动车",
            "教育", "培训", "会计",
            "手艺", "编织", "陶艺", "花艺", "木雕",
            "搬家", "快递", "打印", "手机维修",
        ]
        for hint in industry_hints:
            if hint in message:
                if hint not in keywords:
                    keywords.append(hint)
        return keywords
