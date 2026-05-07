from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class ProductPackagingSkill(BaseSkill):
    name = "包装产品"
    description = "把你的经验包装成可以卖的服务"
    order = 2

    steps = [
        Step(
            id="service_format",
            question="你最舒服的服务方式是什么？",
            options=[
                StepOption(label="一对一电话/视频咨询", value="consultation"),
                StepOption(label="出一份报告/清单", value="report"),
                StepOption(label="陪跑（全程跟着一个客户）", value="coaching"),
                StepOption(label="都不确定，帮我选", value="auto"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="target_customer",
            question="你觉得谁最需要你的经验？谁会愿意付钱？",
            options=[
                StepOption(label="正在装修的业主", value="homeowner"),
                StepOption(label="刚入行的新手", value="newcomer"),
                StepOption(label="小装修公司", value="small_company"),
                StepOption(label="我不确定", value="unsure"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="pricing_comfort",
            question="提到收钱，你最担心什么？",
            options=[
                StepOption(label="不知道该收多少", value="dont_know_price"),
                StepOption(label="怕别人觉得贵", value="afraid_expensive"),
                StepOption(label="不好意思收钱", value="uncomfortable"),
                StepOption(label="担心收了钱做不好", value="fear_delivery"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_product",
            question="我帮你设计了一个服务产品，看看是不是你想要的？如果有想改的，直接告诉我。",
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
        constraints = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }

        phase1_result = state.phase_results.get("1")
        assets = phase1_result.data.get("asset_map", {}) if phase1_result else {}

        if self._llm is None:
            return {"skill_type": "product_packaging", "constraints": constraints}, {}

        assets_str = json.dumps(assets, ensure_ascii=False) if isinstance(assets, dict) else str(assets)
        assessment_tag = ""
        if state.assessment:
            assessment_tag = state.assessment.profile_tag

        prompt = self._prompt_builder.build_product_card_prompt(
            industry="未知行业", assets=assets_str, assessment_tag=assessment_tag,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的产品包装顾问。",
        )
        return {"skill_type": "product_packaging", "constraints": constraints, "product_card": _parse_json(raw)}, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
