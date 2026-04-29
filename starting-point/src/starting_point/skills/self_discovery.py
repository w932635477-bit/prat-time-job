from __future__ import annotations

import json
import logging

from starting_point.confidence.engine import ConfidenceEngine
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

logger = logging.getLogger(__name__)


class SelfDiscoverySkill(BaseSkill):
    name = "认识自己"
    description = "引导用户梳理经验，发现可变现能力"
    order = 1

    steps = [
        Step(
            id="industry",
            question="你在哪个行业干了多少年？",
            options=[
                StepOption(label="建材/装修", value="construction"),
                StepOption(label="餐饮/食品", value="food"),
                StepOption(label="零售/电商", value="retail"),
                StepOption(label="制造业", value="manufacturing"),
                StepOption(label="物流/运输", value="logistics"),
            ],
        ),
        Step(
            id="proud_moment",
            question="过去10年，哪件事你做得比身边大多数同行都稳？",
        ),
        Step(
            id="save_money_story",
            question="讲一个你帮别人省钱或避坑的真实例子，越具体越好。",
            confidence_boost_template="evidence_replay",
        ),
        Step(
            id="insider_knowledge",
            question='你知道哪些"行内人觉得正常，外行根本不知道"的信息？',
        ),
        Step(
            id="people_ask_me",
            question="以前客户或同事最常因为什么来找你？",
        ),
        Step(
            id="price_judgment",
            question='你能判断什么东西"贵了、坑了、不值"？',
        ),
        Step(
            id="unique_resources",
            question="你有没有一类资源是别人短时间拿不到的：报价、渠道、工厂、流程、名单、经验？",
        ),
        Step(
            id="first_100",
            question="如果明天让你只靠经验赚到第一笔100元，你最可能卖什么帮助？",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._confidence = ConfidenceEngine()
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        if self._confidence.detect_negative_emotion(answer):
            evidences = [
                r.free_text or r.answer
                for r in state.step_results
                if r.free_text
            ]
            boost = self._confidence.build_empathetic_response(
                answer, evidences,
            )
            return StepResult(next_step=True, confidence_boost=boost)

        level = self._confidence.assess_from_answer(answer)
        if level.value == "high":
            return StepResult(
                next_step=True,
                confidence_boost=f"很好！你说的这些很具体，对正在装修的人来说非常有价值。",
            )

        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> tuple[dict, dict]:
        answers = []
        for result in state.step_results:
            answers.append(
                f"- {result.step_id}: {result.free_text or result.answer}"
            )

        if self._llm is None:
            output = {
                "skill_type": "self_discovery",
                "answers": answers,
                "total_steps_completed": len(state.step_results),
            }
            return output, {}

        prompt = self._prompt_builder.build_extraction_prompt(
            "\n".join(answers),
        )
        try:
            raw = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            asset_data = self._parse_json(raw)
        except Exception:
            logger.exception("LLM extraction failed, returning raw answers")
            output = {
                "skill_type": "self_discovery",
                "answers": answers,
                "total_steps_completed": len(state.step_results),
            }
            return output, {}

        from starting_point.models import AssetMap, CapabilityItem, ConfidenceLevel
        capabilities = [
            CapabilityItem(
                name=c.get("name", ""),
                description=c.get("description", ""),
                evidence=c.get("evidence", ""),
                estimated_value=c.get("estimated_value"),
            )
            for c in asset_data.get("capabilities", [])
        ]
        conf_str = asset_data.get("confidence_level", "medium")
        asset_map = AssetMap(
            capabilities=capabilities,
            resources=asset_data.get("resources", []),
            confidence_level=ConfidenceLevel(conf_str) if conf_str in ("low", "medium", "high") else ConfidenceLevel.MEDIUM,
            raw_stories=asset_data.get("raw_stories", []),
        )
        output = {
            "skill_type": "self_discovery",
            "answers": answers,
            "asset_map": asset_data,
            "total_steps_completed": len(state.step_results),
        }
        return output, {"asset_map": asset_map}

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        return json.loads(text[start:end])
