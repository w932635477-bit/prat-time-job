from __future__ import annotations

import json
import logging

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

logger = logging.getLogger(__name__)

PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "wechat_moments": "朋友圈",
    "auto": "小红书（推荐新手）",
}


class CustomerAcquisitionSkill(BaseSkill):
    name = "找到客户"
    description = "7天逐日任务，每天一步，帮你接到第一个咨询"
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
            question="我帮你制定了7天行动计划。每天一个任务，30分钟内能完成。准备好了就开始吧！",
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
        asset_map_str = ""
        market_signals_str = ""
        if phase2_result:
            card = phase2_result.data.get("product_card", {})
            service_name = card.get("service_name", "")
            asset_map_str = json.dumps(
                phase2_result.data.get("asset_map", {}), ensure_ascii=False,
            )

        phase1_result = state.phase_results.get("1")
        if phase1_result:
            am = phase1_result.data.get("asset_map", {})
            ms = am.get("market_signals", {})
            if ms:
                market_signals_str = json.dumps(ms, ensure_ascii=False)

        digital_literacy = ""
        time_commitment = ""
        if state.assessment:
            digital_literacy = state.assessment.digital_literacy
            time_commitment = state.assessment.time_commitment

        if self._llm is None:
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "tasks": [],
            }, {}

        prompt = self._prompt_builder.build_daily_tasks_prompt(
            platform=platform_name,
            service_name=service_name or "咨询服务",
            asset_map=asset_map_str or "用户行业经验",
            market_signals=market_signals_str or "暂无",
            digital_literacy=digital_literacy or "intermediate",
            time_commitment=time_commitment or "1-3h",
        )
        try:
            raw = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="你是启点的行动教练。",
            )
            task_data = _parse_json(raw)
        except Exception:
            logger.exception("LLM daily tasks generation failed")
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "tasks": [],
            }, {}

        return {
            "skill_type": "customer_acquisition",
            "platform": platform_name,
            "tasks": task_data.get("tasks", []),
        }, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning("Failed to parse LLM JSON response: %s", text[:200])
        return {"raw": text}
