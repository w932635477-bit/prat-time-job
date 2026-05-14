from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from starting_point.llm.client import LLMClient
from starting_point.db.repos import MessageRepo, StateRepo
from starting_point.models import ProductPackage, ChatResponse, NextStep
from starting_point.prompts.stage_one import SYSTEM_PROMPT, EXTRACT_PROMPT

logger = logging.getLogger(__name__)

MAX_STAGE1_MESSAGES = 6
MAX_EXTRA_ATTEMPTS = 2


class StageOneHandler:
    """Stage 1 product packaging handler.

    Conversation-first approach: LLM chats naturally with the user.
    After enough messages, the handler automatically extracts structured
    product package data in the background.
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
        msg_count = stage_data.get("user_message_count", 0) + 1

        kps = stage_data.get("knowledge_points", [])
        history = await self._msg_repo.load(user_id, stage=1)
        llm_messages = [{"role": h["role"], "content": h["content"]} for h in history]

        if msg_count < MAX_STAGE1_MESSAGES:
            return await self._conversation_turn(
                user_id, llm_messages, kps, stage_data, msg_count, creator_context,
            )

        return await self._extract_and_complete(
            user_id, llm_messages, kps, stage_data, msg_count, creator_context,
        )

    async def _conversation_turn(
        self,
        user_id: str,
        llm_messages: list[dict],
        kps: list[dict],
        stage_data: dict,
        msg_count: int,
        creator_context: str,
    ) -> ChatResponse:
        kp_context = f"已识别的可变现知识点:\n{json.dumps(kps, ensure_ascii=False, indent=2)}\n\n"
        system = SYSTEM_PROMPT + kp_context
        if creator_context:
            system += creator_context

        response = await self._llm.chat(messages=llm_messages, system=system)

        await self._msg_repo.save(user_id, "assistant", response, stage=1)
        new_stage_data = {
            **stage_data,
            "user_message_count": msg_count,
        }
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
        creator_context: str,
    ) -> ChatResponse:
        extract_messages = llm_messages + [
            {"role": "user", "content": "请基于我们的对话，给出完整的产品包装方案。"},
        ]
        kp_context = f"知识点:\n{json.dumps(kps, ensure_ascii=False)}\n\n"
        extract_system = SYSTEM_PROMPT + kp_context + EXTRACT_PROMPT

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
            logger.warning("Stage 1 extraction failed: %s", exc)
            extra_attempts = stage_data.get("extra_attempts", 0) + 1

            if extra_attempts > MAX_EXTRA_ATTEMPTS:
                return await self._force_complete(
                    user_id, stage_data, kps, msg_count,
                )

            fallback_msg = "我需要再了解一些细节，能告诉我你觉得多少钱比较合理吗？"
            await self._msg_repo.save(user_id, "assistant", fallback_msg, stage=1)
            new_stage_data = {
                **stage_data,
                "user_message_count": msg_count,
                "extra_attempts": extra_attempts,
            }
            await self._state_repo.save(user_id, 1, new_stage_data)

            return ChatResponse(
                message=fallback_msg,
                stage=1,
                stage_data=new_stage_data,
                is_complete=False,
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
                description="你的产品已经包装完成！下一步是生成完整的启动套件 — 包含话术模板、发布计划和行动清单。",
                auto_prompt="生成我的启动套件",
            ),
        )

    async def _force_complete(
        self,
        user_id: str,
        stage_data: dict,
        kps: list[dict],
        msg_count: int,
    ) -> ChatResponse:
        first_kp = kps[0] if kps else {}
        kp_id = first_kp.get("id", "kp_1")
        kp_desc = first_kp.get("description", "你的行业经验")
        industry = first_kp.get("industry", "通用")

        default_package = ProductPackage(
            selected_knowledge_id=kp_id,
            product_name=f"{industry}实战经验分享",
            one_liner=f"帮你用{kp_desc}解决实际问题",
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
                description="你的产品已经包装完成！下一步是生成完整的启动套件 — 包含话术模板、发布计划和行动清单。",
                auto_prompt="生成我的启动套件",
            ),
        )
