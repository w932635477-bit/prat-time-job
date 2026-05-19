from __future__ import annotations

import json
import logging

from starting_point.llm.client import LLMClient
from starting_point.db.repos import MessageRepo, StateRepo, KitRepo
from starting_point.models import ChatResponse
from starting_point.confidence.engine import ConfidenceEngine
from starting_point.prompts.stage_two import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class StageTwoHandler:
    """Post-kit coaching handler. Users can ask execution questions."""

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
        self._confidence = ConfidenceEngine()

    async def handle(self, user_id: str, message: str) -> ChatResponse:
        await self._msg_repo.save(user_id, "user", message, stage=2)

        kit = await self._kit_repo.load_by_user(user_id)
        kit_summary = self._build_kit_summary(kit) if kit else "（启动套件数据未找到）"

        history = await self._msg_repo.load(user_id, stage=2)
        messages = self._build_messages(history, message, kit_summary)

        system = SYSTEM_PROMPT.format(kit_summary=kit_summary)
        if self._confidence.detect_negative_emotion(message):
            evidence = []
            if kit and kit.get("product_package"):
                pkg = kit["product_package"]
                evidence.append(f'已经有产品方案"{pkg.get("product_name", "")}"')
            system += "\n\n⚠️ 用户现在情绪低落，有放弃的念头。你必须：先共情认可ta的感受（2-3句话），然后引用ta已经取得的进展来重建信心，最后给一个很小很具体的下一步行动。不要空洞鼓励。"

        response_text = await self._llm.chat(
            messages=messages,
            system=system,
            temperature=0.7,
            max_tokens=1024,
        )

        await self._msg_repo.save(user_id, "assistant", response_text, stage=2)

        return ChatResponse(
            message=response_text,
            stage=2,
            is_complete=False,
        )

    def _build_kit_summary(self, kit: dict) -> str:
        parts = []
        if kit.get("product_package"):
            pkg = kit["product_package"]
            parts.append(f"产品名: {pkg.get('product_name', '')}")
            parts.append(f"定价: {pkg.get('price_range', {})}")
            parts.append(f"目标客户: {pkg.get('target_buyer', '')}")
            parts.append(f"交付方式: {pkg.get('delivery_method', '')}")
        if kit.get("content_direction"):
            parts.append(f"内容方向: {kit['content_direction']}")
        if kit.get("platform_recommendations"):
            platforms = [r.get("platform", "") for r in kit["platform_recommendations"]]
            parts.append(f"推荐平台: {', '.join(platforms)}")
        sm = kit.get("startup_materials", {})
        for key, val in sm.items():
            if key.startswith("_") or not isinstance(val, dict):
                continue
            if val.get("content_calendar"):
                parts.append(f"{key}日历: {len(val['content_calendar'])}天")
        return "\n".join(parts)

    def _build_messages(
        self, history: list[dict], current_message: str, kit_summary: str
    ) -> list[dict]:
        messages = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        if not messages or messages[-1]["content"] != current_message:
            messages.append({"role": "user", "content": current_message})
        return messages
