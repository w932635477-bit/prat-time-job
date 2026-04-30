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
    description = "逐日任务计划，每天一步，帮你接到第一个咨询"
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
            question="我帮你制定了行动计划。每天一个任务，30分钟内能完成。准备好了就开始吧！",
        ),
        Step(
            id="daily_checkin",
            question="今天的任务准备好了。",
            options=[
                StepOption(label="完成了", value="done"),
                StepOption(label="卡住了，需要帮助", value="stuck"),
            ],
            allow_free_text=True,
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        if step_id == "daily_checkin":
            return self._process_checkin(answer, state)
        return StepResult(next_step=True)

    def _process_checkin(self, answer: str, state: UserState) -> StepResult:
        if state.task_plan is None or not state.task_plan.days:
            return StepResult(next_step=True)

        current_idx = state.task_plan.current_day - 1
        if current_idx >= len(state.task_plan.days):
            return StepResult(next_step=True)

        current_task = state.task_plan.days[current_idx]

        if "卡住" in answer or "stuck" in answer.lower():
            stuck_reason = answer.replace("卡住了", "").replace("：", "").replace(":", "").strip()
            if not stuck_reason:
                stuck_reason = "用户未说明具体原因"
            updated_day = current_task.model_copy(update={
                "status": "stuck",
                "stuck_reason": stuck_reason,
            })
            updated_days = list(state.task_plan.days)
            updated_days[current_idx] = updated_day
            updated_plan = state.task_plan.model_copy(update={"days": updated_days})

            return StepResult(
                next_step=False,
                confidence_boost=f"卡住很正常，让我帮你分析一下「{stuck_reason}」这个问题。",
                deliverable={"task_plan_update": updated_plan.model_dump(), "stuck": True},
            )

        # Mark as done
        from datetime import datetime
        updated_day = current_task.model_copy(update={
            "status": "done",
            "completed_at": datetime.now(),
        })
        updated_days = list(state.task_plan.days)
        updated_days[current_idx] = updated_day
        next_day = state.task_plan.current_day + 1
        is_all_done = next_day > state.task_plan.total_days

        updated_plan = state.task_plan.model_copy(update={
            "days": updated_days,
            "current_day": next_day,
            "status": "completed" if is_all_done else "active",
        })

        if is_all_done:
            return StepResult(
                next_step=True,
                confidence_boost="所有任务都完成了，你做到了！",
                deliverable={"task_plan_update": updated_plan.model_dump()},
            )

        return StepResult(
            next_step=False,
            confidence_boost=f"第{current_task.day}天完成！明天继续。",
            deliverable={"task_plan_update": updated_plan.model_dump()},
        )

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

        suggested_days = self._calculate_suggested_days(
            digital_literacy or "intermediate",
            time_commitment or "1-3h",
        )

        if self._llm is None:
            from starting_point.models import TaskDay, TaskPlan
            fallback_days = [
                TaskDay(day=1, task=f"在{platform_name}注册账号，完善个人资料", platform=platform_name, why="先让客户能找到你", success_signal="账号上线"),
                TaskDay(day=2, task=f"在{platform_name}发第一篇内容，分享你的行业经验", platform=platform_name, why="让内容替你说话", success_signal="发布成功"),
                TaskDay(day=3, task="回复至少3个同行业内容的评论", platform=platform_name, why="混个脸熟", success_signal="有人注意到你"),
            ]
            task_plan = TaskPlan(total_days=len(fallback_days), current_day=1, days=fallback_days, platform=platform_name)
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "tasks": [d.model_dump() for d in fallback_days],
                "suggested_days": len(fallback_days),
            }, {"task_plan": task_plan}

        prompt = self._prompt_builder.build_daily_tasks_prompt(
            platform=platform_name,
            service_name=service_name or "咨询服务",
            asset_map=asset_map_str or "用户行业经验",
            market_signals=market_signals_str or "暂无",
            digital_literacy=digital_literacy or "intermediate",
            time_commitment=time_commitment or "1-3h",
            suggested_days=suggested_days,
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
                "suggested_days": suggested_days,
            }, {}

        from starting_point.models import TaskDay, TaskPlan
        task_days = []
        for t in task_data.get("tasks", []):
            task_days.append(TaskDay(
                day=t.get("day", len(task_days) + 1),
                task=t.get("task", ""),
                platform=t.get("platform", platform_name),
                estimated_time=t.get("estimated_time", "30分钟"),
                why=t.get("why", ""),
                success_signal=t.get("success_signal", ""),
            ))

        total = len(task_days) if task_days else suggested_days
        task_plan = TaskPlan(
            total_days=total,
            current_day=1,
            days=task_days,
            platform=platform_name,
        )

        return {
            "skill_type": "customer_acquisition",
            "platform": platform_name,
            "tasks": task_data.get("tasks", []),
            "suggested_days": total,
        }, {"task_plan": task_plan}

    async def generate_rescue(
        self, day: int, task: str, platform: str,
        stuck_reason: str, completed_days: int,
    ) -> dict | None:
        if self._llm is None:
            return None
        prompt = self._prompt_builder.build_stuck_rescue_prompt(
            day=day, task=task, platform=platform,
            stuck_reason=stuck_reason, completed_days=completed_days,
        )
        try:
            raw = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="你是启点的行动教练。",
                temperature=0.5,
                max_tokens=1024,
            )
            return _parse_json(raw)
        except Exception:
            logger.exception("LLM rescue generation failed")
            return None

    def _calculate_suggested_days(self, digital_literacy: str, time_commitment: str) -> int:
        base = 14
        if digital_literacy in ("beginner", "low", "新手"):
            base = 21
        elif digital_literacy in ("advanced", "high", "熟练"):
            base = 14

        if "1h" in time_commitment or "30" in time_commitment:
            base = min(base + 7, 30)

        return min(base, 30)


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning("Failed to parse LLM JSON response: %s", text[:200])
        return {"raw": text}
