from __future__ import annotations

import json
import logging

from starting_point.confidence.engine import ConfidenceEngine
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

logger = logging.getLogger(__name__)


class GrowthSkill(BaseSkill):
    name = "转起来"
    description = "首单之后，持续赚钱"
    order = 5

    steps = [
        Step(
            id="deal_result",
            question="第一单完成得怎么样？",
            options=[
                StepOption(label="完成了！客户很满意", value="completed_happy"),
                StepOption(label="完成了，但有点波折", value="completed_bumpy"),
                StepOption(label="没完成，客户跑了", value="lost"),
                StepOption(label="还没完成，还在沟通中", value="in_progress"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="deal_details",
            question="跟我说说：客户花了多少钱？是怎么找到你的？",
        ),
        Step(
            id="next_goal",
            question="接下来你最想做什么？",
            options=[
                StepOption(label="多接几个客户", value="more_clients"),
                StepOption(label="把价格提上去", value="raise_price"),
                StepOption(label="让老客户帮我推荐新客户", value="referrals"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="action_this_week",
            question="这周你准备做什么？选一个先做起来。",
        ),
        Step(
            id="confirm_growth",
            question="这是你的增长计划。记住：你已经是做过一单的人了，这不是练习了。",
        ),
    ]

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._confidence = ConfidenceEngine()
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        if step_id == "deal_result":
            if answer in ("没完成，客户跑了", "lost"):
                return StepResult(
                    next_step=True,
                    confidence_boost="客户跑了很正常，做生意十次成交两三次就是好成绩。关键是搞清楚为什么跑，下次就不一样了。",
                )
            if answer in ("完成了！客户很满意", "completed_happy"):
                return StepResult(
                    next_step=True,
                    confidence_boost="你做到了！从今天开始，你不是一个失业的人了——你是一个有客户的人。",
                )
            return StepResult(next_step=True)

        if step_id == "deal_details":
            if self._confidence.detect_negative_emotion(answer):
                return StepResult(
                    next_step=True,
                    confidence_boost="说出来就是进步。我们一起看看接下来怎么调整。",
                )
            return StepResult(next_step=True)

        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> tuple[dict, dict]:
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

        answers = {r.step_id: r.free_text or r.answer for r in state.step_results}
        deal_result = answers.get("deal_result", "in_progress")
        deal_details = answers.get("deal_details", "")

        if self._llm is None:
            return {"skill_type": "growth", "service_name": service_name}, {}

        prompt = self._prompt_builder.build_growth_prompt(
            service_name=service_name,
            first_deal_price=first_deal_price or 299,
            channel=channel,
            deal_result=deal_result,
            deal_details=deal_details,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的增长顾问。",
        )
        return {"skill_type": "growth", "growth_plan": _parse_json(raw)}, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
