from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class GrowthSkill(BaseSkill):
    name = "转起来"
    description = "首单之后，持续赚钱"
    order = 5

    steps = [
        Step(
            id="deal_status",
            question="恭喜！第一单完成了吗？",
            options=[
                StepOption(label="完成了！客户很满意", value="completed"),
                StepOption(label="完成了，但有点波折", value="completed_bumpy"),
                StepOption(label="还没完成，还在沟通中", value="in_progress"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_growth",
            question="这是你的增长计划。从今天开始，你不再是一个失业的人了——你是一个有自己的小生意的人。",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        phase2 = state.phase_results.get("2")
        product_card = phase2.data.get("product_card", {}) if phase2 else {}
        service_name = product_card.get("service_name", "")

        first_deal_price = 0
        phase4 = state.phase_results.get("4")
        if phase4:
            toolkit = phase4.data.get("toolkit", {})
            first_deal_price = toolkit.get("first_deal_price", 0)

        channel = "xiaohongshu"
        phase3 = state.phase_results.get("3")
        if phase3:
            channel = phase3.data.get("platform_key", channel)

        if self._llm is None:
            return {"skill_type": "growth", "service_name": service_name}

        prompt = self._prompt_builder.build_growth_prompt(
            service_name=service_name,
            first_deal_price=first_deal_price or 299,
            channel=channel,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的增长顾问。",
        )
        return {"skill_type": "growth", "growth_plan": _parse_json(raw)}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
