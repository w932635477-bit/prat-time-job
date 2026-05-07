from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import LLMClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class AssessmentSkill(BaseSkill):
    name = "起跑评估"
    description = "评估你的起点，制定个性化策略"
    order = 0

    steps = [
        Step(
            id="digital_literacy",
            question="你平时用手机做什么？",
            options=[
                StepOption(label="打电话、发微信", value="basic"),
                StepOption(label="刷抖音、看小红书", value="intermediate"),
                StepOption(label="发过视频或帖子", value="advanced"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="mental_readiness",
            question="你现在最想的是什么？",
            options=[
                StepOption(label="找到一份工作", value="job_seeking"),
                StepOption(label="试试自己干", value="ready"),
                StepOption(label="不确定，想先看看", value="exploring"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="time_commitment",
            question="你每天能花多少时间在这件事上？",
            options=[
                StepOption(label="1小时以内", value="<1h"),
                StepOption(label="1到3小时", value="1-3h"),
                StepOption(label="3小时以上", value=">3h"),
            ],
        ),
        Step(
            id="financial_pressure",
            question="你现在的经济状况？",
            options=[
                StepOption(label="还有3个月以上缓冲", value="comfortable"),
                StepOption(label="1到3个月", value="moderate"),
                StepOption(label="一个月内很紧张", value="urgent"),
            ],
            allow_free_text=True,
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
        answers = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }

        if self._llm is None:
            output = {"skill_type": "assessment", "answers": answers}
            return output, {}

        prompt = self._prompt_builder.build_assessment_strategy_prompt(
            digital_literacy=answers.get("digital_literacy", "basic"),
            mental_readiness=answers.get("mental_readiness", "exploring"),
            time_commitment=answers.get("time_commitment", "1-3h"),
            financial_pressure=answers.get("financial_pressure", "moderate"),
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的用户评估顾问。",
        )
        strategy = _parse_json(raw)
        from starting_point.models import UserAssessment
        assessment_updates = {
            "digital_literacy": answers.get("digital_literacy", ""),
            "mental_readiness": answers.get("mental_readiness", ""),
            "time_commitment": answers.get("time_commitment", ""),
            "financial_pressure": answers.get("financial_pressure", ""),
            "profile_tag": strategy.get("profile_tag", ""),
            "content_pace": strategy.get("content_pace", "normal"),
            "first_milestone": strategy.get("first_milestone", ""),
            "expectation_tone": strategy.get("expectation_tone", ""),
        }
        output = {"skill_type": "assessment", "answers": answers, "strategy": strategy}
        return output, {"assessment": UserAssessment(**assessment_updates)}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
