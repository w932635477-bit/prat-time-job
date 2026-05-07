from __future__ import annotations

import json
import logging

from starting_point.confidence.engine import ConfidenceEngine
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

logger = logging.getLogger(__name__)


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
            id="pricing_concern",
            question="提到报价，你现在最担心什么？",
            options=[
                StepOption(label="不知道该报多少", value="dont_know"),
                StepOption(label="怕报贵了吓跑客户", value="fear_too_high"),
                StepOption(label="怕报低了亏自己", value="fear_too_low"),
                StepOption(label="不好意思开口收钱", value="uncomfortable"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="payment_comfort",
            question="你打算怎么收钱？",
            options=[
                StepOption(label="微信转账", value="wechat_transfer"),
                StepOption(label="支付宝", value="alipay"),
                StepOption(label="没想过，不知道怎么收", value="unsure"),
                StepOption(label="先免费做一次试试", value="free_trial"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="delivery_readiness",
            question="如果客户今天就说'好，我买了'，你准备好交付了吗？",
            options=[
                StepOption(label="准备好了，流程我清楚", value="ready"),
                StepOption(label="大概知道，但不确定细节", value="roughly"),
                StepOption(label="没想过交付的事", value="not_ready"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_tools",
            question="我帮你准备好了完整的首单工具包。仔细看看，有不懂的随时问我。",
        ),
    ]

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._confidence = ConfidenceEngine()
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        if step_id == "customer_status":
            if answer in ("还没有客户，先学学", "no_customer_yet"):
                return StepResult(
                    next_step=True,
                    confidence_boost="没关系！先准备好话术，客户来了你就不慌了。练一遍比看十遍有用。",
                )
            return StepResult(
                next_step=True,
                confidence_boost="有人来找你了，说明你发的内容起作用了。接下来我们一步步搞定它。",
            )

        if step_id == "pricing_concern":
            if self._confidence.detect_negative_emotion(answer):
                phase2 = state.phase_results.get("2")
                product_card = phase2.data.get("product_card", {}) if phase2 else {}
                service_name = product_card.get("service_name", "你的服务")
                return StepResult(
                    next_step=True,
                    confidence_boost=f"担心价格很正常。记住，{service_name}不是你在卖时间，是你在帮别人避坑。避一个坑值多少钱，客户自己心里有数。",
                )
            return StepResult(next_step=True)

        if step_id == "delivery_readiness":
            if answer in ("没想过交付的事", "not_ready") or self._confidence.detect_negative_emotion(answer):
                return StepResult(
                    next_step=True,
                    confidence_boost="能说出'没准备好'的人，反而比装懂的人更靠谱。我来帮你把交付步骤理清楚。",
                )
            return StepResult(next_step=True)

        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> tuple[dict, dict]:
        phase2 = state.phase_results.get("2")
        product_card = phase2.data.get("product_card", {}) if phase2 else {}
        service_name = product_card.get("service_name", "")
        pricing = json.dumps(product_card.get("pricing", {}), ensure_ascii=False)
        service_flow = "\n".join(product_card.get("service_flow", []))

        answers = {r.step_id: r.free_text or r.answer for r in state.step_results}
        customer_status = answers.get("customer_status", "no_customer_yet")
        pricing_concern = answers.get("pricing_concern", "dont_know")
        payment_comfort = answers.get("payment_comfort", "unsure")
        delivery_readiness = answers.get("delivery_readiness", "not_ready")

        if self._llm is None:
            return {"skill_type": "first_deal", "product_card": product_card}, {}

        prompt = self._prompt_builder.build_first_deal_prompt(
            service_name=service_name,
            pricing=pricing,
            service_flow=service_flow,
            customer_status=customer_status,
            pricing_concern=pricing_concern,
            payment_comfort=payment_comfort,
            delivery_readiness=delivery_readiness,
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
