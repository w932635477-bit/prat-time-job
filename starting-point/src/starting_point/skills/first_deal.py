from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class FirstDealSkill(BaseSkill):
    name = "完成首单"
    description = "客户来了，教你搞定第一单"
    order = 4

    steps = [
        Step(
            id="customer_status",
            question="客户来了！现在是什么情况？",
            options=[
                StepOption(label="有人在私信问我了", value="inquiry"),
                StepOption(label="有人问价格了", value="price_asked"),
                StepOption(label="有人想约咨询了", value="wants_consultation"),
                StepOption(label="还没有客户，先学学", value="no_customer_yet"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_tools",
            question="我已经帮你准备好了沟通话术、报价公式和交付清单。仔细看看，有不懂的随时问我。",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> tuple[dict, dict]:
        phase2 = state.phase_results.get("2")
        product_card = phase2.data.get("product_card", {}) if phase2 else {}
        service_name = product_card.get("service_name", "")
        pricing = json.dumps(product_card.get("pricing", {}), ensure_ascii=False)
        service_flow = "\n".join(product_card.get("service_flow", []))

        if self._llm is None:
            return {"skill_type": "first_deal", "product_card": product_card}, {}

        prompt = self._prompt_builder.build_first_deal_prompt(
            service_name=service_name, pricing=pricing, service_flow=service_flow,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的首单教练。",
        )
        return {"skill_type": "first_deal", "toolkit": _parse_json(raw)}, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
