from __future__ import annotations

import json
import logging

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

logger = logging.getLogger(__name__)

PLATFORM_NAMES = {
    "xianyu": "闲鱼",
    "xiaohongshu": "小红书",
    "wechat": "朋友圈",
}


class TakeActionSkill(BaseSkill):
    name = "开张行动"
    description = "生成首发文案，帮你上线（简化版）"
    order = 3

    steps = [
        Step(
            id="platform",
            question="你想先在哪个平台发布？",
            options=[
                StepOption(label="闲鱼", value="xianyu"),
                StepOption(label="小红书", value="xiaohongshu"),
                StepOption(label="朋友圈", value="wechat"),
            ],
        ),
        Step(
            id="confirm_launch",
            question="文案已生成！你准备发布吗？如果有想修改的地方，告诉我。",
        ),
    ]

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> tuple[dict, dict]:
        platform_result = next(
            (r for r in state.step_results if r.step_id == "platform"),
            None,
        )
        platform_key = (
            platform_result.selected_option or platform_result.answer
            if platform_result
            else "xianyu"
        )
        platform_name = PLATFORM_NAMES.get(platform_key, platform_key)

        if self._llm is None:
            return {
                "skill_type": "take_action",
                "platform": platform_name,
                "status": "content_generated",
            }, {}

        offer = state.selected_offer
        offer_str = (
            json.dumps(offer.model_dump(), ensure_ascii=False)
            if offer
            else "暂无offer"
        )

        background_parts = []
        for r in state.step_results:
            background_parts.append(f"{r.step_id}: {r.free_text or r.answer}")
        background = "\n".join(background_parts) if background_parts else "用户未提供背景"

        prompt = self._prompt_builder.build_content_prompt(
            platform=platform_name,
            offer=offer_str,
            background=background,
        )
        try:
            raw = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            content_data = self._parse_json(raw)
        except Exception:
            logger.exception("LLM content generation failed")
            return {
                "skill_type": "take_action",
                "platform": platform_name,
                "status": "content_generation_failed",
            }, {}

        return {
            "skill_type": "take_action",
            "platform": platform_name,
            "content": content_data,
            "status": "content_generated",
        }, {}

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        return json.loads(text[start:end])
