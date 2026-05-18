from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from starting_point.llm.client import LLMClient
from starting_point.db.repos import MessageRepo, StateRepo
from starting_point.models import StageZeroOutput, ChatResponse, NextStep
from starting_point.prompts.stage_zero import SYSTEM_PROMPT, FORCE_EXTRACT_SUFFIX, WIKI_USAGE_NOTE
from starting_point.utils.json import extract_json
from starting_point.wiki import HINTS, get_wiki_sections

logger = logging.getLogger(__name__)

MAX_STAGE0_MESSAGES = 10

# Sections useful for discovery probing (lighter than Stage 1)
_STAGE0_WIKI_SECTIONS = ["常见可变现知识点", "同行案例拆解", "用户常见顾虑"]


class StageZeroHandler:
    """Stage 0 discovery handler with LLM-internal state machine.

    The LLM decides when to output JSON; code tracks message count
    and forces extraction after MAX_STAGE0_MESSAGES.
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
        # Save user message
        await self._msg_repo.save(user_id, "user", message, stage=0)

        # Load state and history
        state = await self._state_repo.load(user_id)
        if state is None:
            state = {
                "current_stage": 0,
                "stage_data": {
                    "user_message_count": 0,
                    "status": "collecting",
                    "knowledge_points": [],
                    "force_extract_triggered": False,
                },
            }

        stage_data = state["stage_data"]
        user_msg_count = stage_data.get("user_message_count", 0) + 1

        # Load full history
        history = await self._msg_repo.load(user_id, stage=0)

        # Build messages for LLM
        llm_messages = [{"role": h["role"], "content": h["content"]} for h in history]

        # Inject wiki knowledge base into system prompt
        wiki_context = self._build_wiki_context(llm_messages)

        # Determine if force-extract mode
        system_prompt = SYSTEM_PROMPT
        if wiki_context:
            system_prompt += wiki_context + WIKI_USAGE_NOTE
        if creator_context:
            system_prompt += creator_context
        if user_msg_count >= MAX_STAGE0_MESSAGES:
            system_prompt += FORCE_EXTRACT_SUFFIX
            stage_data = {
                **stage_data,
                "force_extract_triggered": True,
            }

        # Call LLM
        response_text = await self._llm.chat(
            messages=llm_messages,
            system=system_prompt,
        )

        # Try to parse as JSON
        parsed = extract_json(response_text)
        if parsed is not None and "knowledge_points" in parsed:
            return await self._handle_json_output(
                user_id, parsed, stage_data, user_msg_count,
            )

        # Plain text response - save and return
        await self._msg_repo.save(user_id, "assistant", response_text, stage=0)
        new_stage_data = {
            **stage_data,
            "user_message_count": user_msg_count,
        }
        await self._state_repo.save(user_id, 0, new_stage_data)

        return ChatResponse(
            message=response_text,
            stage=0,
            stage_data=new_stage_data,
            is_complete=False,
        )

    @staticmethod
    def _detect_industry(messages: list[dict]) -> str:
        """Scan conversation for industry keywords, return wiki page name or empty string."""
        all_text = " ".join(m.get("content", "") for m in messages)
        # Direct industry page name match (highest priority)
        for name in ("建材", "餐饮", "家政", "内容变现实战案例"):
            if name in all_text:
                return name
        # Keyword-to-industry mapping
        for keyword, mapped in HINTS.items():
            if keyword in all_text:
                return mapped
        return ""

    def _build_wiki_context(self, messages: list[dict]) -> str:
        """Load relevant wiki sections based on detected industry."""
        industry = self._detect_industry(messages)
        if not industry:
            return ""
        sections = get_wiki_sections(industry, _STAGE0_WIKI_SECTIONS)
        if not sections:
            return ""
        return f"\n\n## 行业知识库（{industry}）\n{sections}"

    async def _handle_json_output(
        self,
        user_id: str,
        parsed: dict,
        stage_data: dict,
        user_msg_count: int,
    ) -> ChatResponse:
        try:
            validated = StageZeroOutput.model_validate(parsed)
            # Valid with 3+ points -> stage complete
            new_stage_data = {
                **stage_data,
                "user_message_count": user_msg_count,
                "status": "completed",
                "knowledge_points": [kp.model_dump() for kp in validated.knowledge_points],
            }
            await self._state_repo.save(user_id, 1, new_stage_data)

            return ChatResponse(
                message=validated.summary,
                stage=1,
                stage_data=new_stage_data,
                is_complete=True,
                next_step=NextStep(
                    title="包装你的知识产品",
                    description="我们已经找到了你的经验亮点。下一步是把它们包装成一个可以卖的产品 — 确定目标客户、定价和交付方式。",
                    auto_prompt="好，帮我包装成产品",
                ),
            )
        except ValidationError:
            # JSON didn't validate (e.g. < 3 points) -> continue conversation
            logger.warning("Stage 0 JSON validation failed, continuing conversation")
            follow_up = "你提取的知识点还不够，请继续提问来发现更多可变现的经验。"
            await self._msg_repo.save(user_id, "assistant", follow_up, stage=0)
            new_stage_data = {
                **stage_data,
                "user_message_count": user_msg_count,
            }
            await self._state_repo.save(user_id, 0, new_stage_data)

            return ChatResponse(
                message=follow_up,
                stage=0,
                stage_data=new_stage_data,
                is_complete=False,
            )
