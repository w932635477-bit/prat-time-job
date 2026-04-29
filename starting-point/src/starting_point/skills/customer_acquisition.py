from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "wechat_moments": "朋友圈",
    "auto": "小红书（推荐新手）",
}

WEEK_THEMES = [
    {"week": 1, "theme": "试水期", "pieces": 7},
    {"week": 2, "theme": "找感觉期", "pieces": 7},
    {"week": 3, "theme": "突破期", "pieces": 8},
    {"week": 4, "theme": "收获期", "pieces": 8},
]


class CustomerAcquisitionSkill(BaseSkill):
    name = "找到客户"
    description = "30天内容计划，帮你获得第一个咨询"
    order = 3

    steps = [
        Step(
            id="platform_choice",
            question="你想先在哪个平台开始发内容？",
            options=[
                StepOption(label="抖音（短视频）", value="douyin"),
                StepOption(label="小红书（图文笔记）", value="xiaohongshu"),
                StepOption(label="朋友圈（私域）", value="wechat_moments"),
                StepOption(label="我都不熟，帮我选", value="auto"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="content_readiness",
            question="你之前发过类似的内容吗？",
            options=[
                StepOption(label="从来没发过", value="never"),
                StepOption(label="发过但没人看", value="tried"),
                StepOption(label="有人看过但没咨询", value="some_views"),
            ],
        ),
        Step(
            id="confirm_plan",
            question="我帮你制定了一个30天内容计划。第一周的内容已经准备好了，你可以先看看。准备好了就开始吧！",
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
        platform_result = next(
            (r for r in state.step_results if r.step_id == "platform_choice"), None,
        )
        platform_key = (platform_result.free_text or platform_result.answer) if platform_result else "xiaohongshu"
        platform_name = PLATFORM_NAMES.get(platform_key, platform_key)

        phase2_result = state.phase_results.get("2")
        service_name = ""
        if phase2_result:
            card = phase2_result.data.get("product_card", {})
            service_name = card.get("service_name", "")

        if self._llm is None:
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "platform_key": platform_key,
                "remaining_weeks": WEEK_THEMES[1:],
            }, {}

        week_info = WEEK_THEMES[0]
        prompt = self._prompt_builder.build_content_week_prompt(
            week=week_info["week"],
            theme=week_info["theme"],
            industry="未知",
            platform=platform_name,
            service_name=service_name,
            pieces=week_info["pieces"],
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的内容策划师。",
        )
        return {
            "skill_type": "customer_acquisition",
            "platform": platform_name,
            "platform_key": platform_key,
            "week1_content": _parse_json(raw),
            "remaining_weeks": WEEK_THEMES[1:],
        }, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
