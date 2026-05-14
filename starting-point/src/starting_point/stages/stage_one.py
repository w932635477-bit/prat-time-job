from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.db.repos import MessageRepo, StateRepo
from starting_point.models import ProductPackage, ChatResponse, NextStep
from starting_point.prompts.stage_one import SYSTEM_PROMPT, EXTRACT_PROMPT, READINESS_CHECK_SUFFIX

logger = logging.getLogger(__name__)

MIN_STAGE1_MESSAGES = 4
MAX_STAGE1_MESSAGES = 12

_STAGE_ZERO_SUMMARY_LIMIT = 10

# Signals that the LLM has produced a complete product plan
_PLAN_SIGNALS = (
    "方案就这么定了",
    "方案如下",
    "你的服务产品",
    "产品名称",
    "你的产品方案",
    "就这么定了",
    "产品方案已经",
)


class StageOneHandler:
    """Stage 1 product packaging handler.

    Loads Stage 0 conversation context to maintain continuity.
    Uses flexible completion based on readiness, not just message count.
    """

    def __init__(
        self,
        llm: LLMClient,
        msg_repo: MessageRepo,
        state_repo: StateRepo,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm
        self._msg_repo = msg_repo
        self._state_repo = state_repo
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def handle(self, user_id: str, message: str, creator_context: str = "") -> ChatResponse:
        await self._msg_repo.save(user_id, "user", message, stage=1)

        state = await self._state_repo.load(user_id)
        stage_data = state["stage_data"] if state else {}
        msg_count = stage_data.get("user_message_count", 0) + 1

        kps = stage_data.get("knowledge_points", [])

        stage_zero_history = await self._msg_repo.load_up_to_stage(user_id, 0)
        stage_zero_summary = self._summarize_stage_zero(stage_zero_history)

        stage_one_history = await self._msg_repo.load(user_id, 1)
        llm_messages = [{"role": h["role"], "content": h["content"]} for h in stage_one_history]

        if msg_count < MAX_STAGE1_MESSAGES:
            return await self._conversation_turn(
                user_id, llm_messages, kps, stage_data, msg_count,
                stage_zero_summary, creator_context,
            )

        return await self._extract_and_complete(
            user_id, llm_messages, kps, stage_data, msg_count,
            stage_zero_summary, creator_context,
        )

    async def _conversation_turn(
        self,
        user_id: str,
        llm_messages: list[dict],
        kps: list[dict],
        stage_data: dict,
        msg_count: int,
        stage_zero_summary: str,
        creator_context: str,
    ) -> ChatResponse:
        kp_context = f"\n已识别的可变现知识点:\n{json.dumps(kps, ensure_ascii=False, indent=2)}\n"
        creator_section = f"\n{creator_context}" if creator_context else ""
        summary_section = f"\n你们之前的对话摘要:\n{stage_zero_summary}\n" if stage_zero_summary else ""

        system = SYSTEM_PROMPT.format(
            stage_zero_summary=summary_section,
            knowledge_points=kp_context,
            creator_context=creator_section,
        )

        if msg_count >= MIN_STAGE1_MESSAGES:
            system += READINESS_CHECK_SUFFIX.format(count=msg_count)

        response = await self._llm.chat(messages=llm_messages, system=system)

        await self._msg_repo.save(user_id, "assistant", response, stage=1)
        new_stage_data = {
            **stage_data,
            "user_message_count": msg_count,
        }

        # Early extraction: if LLM produced a complete plan and we're past MIN messages
        if msg_count >= MIN_STAGE1_MESSAGES and self._has_plan_summary(response):
            extract_result = await self._try_extract(
                user_id, llm_messages, kps, stage_data, msg_count,
                stage_zero_summary, creator_context, response,
            )
            if extract_result is not None:
                return extract_result

        await self._state_repo.save(user_id, 1, new_stage_data)

        return ChatResponse(
            message=response,
            stage=1,
            stage_data=new_stage_data,
            is_complete=False,
        )

    async def _extract_and_complete(
        self,
        user_id: str,
        llm_messages: list[dict],
        kps: list[dict],
        stage_data: dict,
        msg_count: int,
        stage_zero_summary: str,
        creator_context: str,
    ) -> ChatResponse:
        extract_messages = llm_messages + [
            {"role": "user", "content": "请基于我们的对话，给出完整的产品包装方案。"},
        ]

        kp_context = f"\n知识点:\n{json.dumps(kps, ensure_ascii=False)}\n"
        creator_section = f"\n{creator_context}" if creator_context else ""
        summary_section = f"\n对话背景:\n{stage_zero_summary}\n" if stage_zero_summary else ""

        extract_system = SYSTEM_PROMPT.format(
            stage_zero_summary=summary_section,
            knowledge_points=kp_context,
            creator_context=creator_section,
        ) + "\n\n" + EXTRACT_PROMPT

        try:
            validated = await self._llm.chat_json(
                messages=extract_messages,
                schema=ProductPackage,
                system=extract_system,
            )
            return await self._complete_stage(
                user_id, validated, stage_data, msg_count,
            )
        except (ValueError, ValidationError) as exc:
            logger.warning("Stage 1 extraction failed, force-completing: %s", exc)
            return await self._force_complete(
                user_id, stage_data, kps, msg_count, stage_zero_summary,
            )

    async def _complete_stage(
        self,
        user_id: str,
        package: ProductPackage,
        stage_data: dict,
        msg_count: int,
    ) -> ChatResponse:
        new_stage_data = {
            **stage_data,
            "product_package": package.model_dump(),
            "user_message_count": msg_count,
        }
        await self._state_repo.save(user_id, 2, new_stage_data)

        summary = (
            f"你的产品方案已经整理好了！\n\n"
            f"**产品名称：** {package.product_name}\n"
            f"**一句话：** {package.one_liner}\n"
            f"**目标客户：** {package.target_buyer}\n"
            f"**建议定价：** {package.price_range.min}-{package.price_range.max} 元\n"
            f"**交付方式：** {package.delivery_method}"
        )

        return ChatResponse(
            message=summary,
            stage=2,
            stage_data=new_stage_data,
            is_complete=True,
            next_step=NextStep(
                title="生成你的启动套件",
                description="你的产品已经包装完成！下一步是生成完整的启动套件 -- 包含话术模板、发布计划和行动清单。",
                auto_prompt="生成我的启动套件",
            ),
        )

    async def _force_complete(
        self,
        user_id: str,
        stage_data: dict,
        kps: list[dict],
        msg_count: int,
        stage_zero_summary: str,
    ) -> ChatResponse:
        primary_kp = kps[0] if kps else {}
        kp_id = primary_kp.get("id", "kp_1")
        kp_desc = primary_kp.get("description", "你的行业经验")
        industry = primary_kp.get("industry", "通用")

        all_industries = list({kp.get("industry", "") for kp in kps if kp.get("industry")})
        industry = all_industries[0] if all_industries else "通用"

        all_descriptions = [kp.get("description", "") for kp in kps if kp.get("description")]
        combined_desc = "、".join(all_descriptions[:3]) if all_descriptions else kp_desc

        default_package = ProductPackage(
            selected_knowledge_id=kp_id,
            product_name=f"{industry}实战经验分享",
            one_liner=f"帮你用{combined_desc}解决实际问题",
            target_buyer=f"想进入{industry}行业的新手",
            service_type="consultation",
            price_range={"min": 49, "max": 199},
            delivery_method="一对一线上咨询，每次45分钟",
        )

        logger.info("Stage 1 force-completing with default package for user %s", user_id)

        new_stage_data = {
            **stage_data,
            "product_package": default_package.model_dump(),
            "user_message_count": msg_count,
            "force_completed": True,
        }
        await self._state_repo.save(user_id, 2, new_stage_data)

        summary = (
            f"我已经根据咱们的对话整理了一个初步方案：\n\n"
            f"**产品名称：** {default_package.product_name}\n"
            f"**目标客户：** {default_package.target_buyer}\n"
            f"**建议定价：** {default_package.price_range.min}-{default_package.price_range.max} 元\n"
            f"**交付方式：** {default_package.delivery_method}\n\n"
            f"这个方案可以后续调整。接下来我们生成你的启动套件！"
        )

        return ChatResponse(
            message=summary,
            stage=2,
            stage_data=new_stage_data,
            is_complete=True,
            next_step=NextStep(
                title="生成你的启动套件",
                description="你的产品已经包装完成！下一步是生成完整的启动套件 -- 包含话术模板、发布计划和行动清单。",
                auto_prompt="生成我的启动套件",
            ),
        )

    def _has_plan_summary(self, response: str) -> bool:
        """Check if the LLM response contains a structured product plan."""
        response_lower = response.lower()
        return any(signal in response for signal in _PLAN_SIGNALS) or (
            "**产品" in response and "**定价" in response
        )

    async def _try_extract(
        self,
        user_id: str,
        llm_messages: list[dict],
        kps: list[dict],
        stage_data: dict,
        msg_count: int,
        stage_zero_summary: str,
        creator_context: str,
        last_response: str,
    ) -> ChatResponse | None:
        """Attempt early extraction. Returns None if extraction fails."""
        kp_context = f"\n知识点:\n{json.dumps(kps, ensure_ascii=False)}\n"
        creator_section = f"\n{creator_context}" if creator_context else ""
        summary_section = f"\n对话背景:\n{stage_zero_summary}\n" if stage_zero_summary else ""

        extract_system = SYSTEM_PROMPT.format(
            stage_zero_summary=summary_section,
            knowledge_points=kp_context,
            creator_context=creator_section,
        ) + "\n\n" + EXTRACT_PROMPT

        extract_messages = llm_messages + [
            {"role": "user", "content": "请基于我们的对话，给出完整的产品包装方案。"},
        ]

        try:
            validated = await self._llm.chat_json(
                messages=extract_messages,
                schema=ProductPackage,
                system=extract_system,
            )
            return await self._complete_stage(user_id, validated, stage_data, msg_count)
        except (ValueError, ValidationError) as exc:
            logger.info("Early extraction not ready yet: %s", exc)
            return None

    def _summarize_stage_zero(self, history: list[dict[str, str]]) -> str:
        if not history:
            return ""

        user_statements = []
        assistant_questions = []

        for msg in history:
            content = msg.get("content", "")
            role = msg.get("role", "")
            if role == "user" and len(content) > 5:
                user_statements.append(content[:200])
            elif role == "assistant" and ("?" in content or "？" in content) and len(content) < 200:
                assistant_questions.append(content[:200])

        if not user_statements:
            return ""

        recent_statements = user_statements[-_STAGE_ZERO_SUMMARY_LIMIT:]
        summary_parts = ["用户说的关键内容："]
        for i, stmt in enumerate(recent_statements, 1):
            summary_parts.append(f"  {i}. {stmt}")

        if assistant_questions:
            recent_questions = assistant_questions[-3:]
            summary_parts.append("\n你问过的关键问题：")
            for q in recent_questions:
                summary_parts.append(f"  - {q}")

        return "\n".join(summary_parts)
