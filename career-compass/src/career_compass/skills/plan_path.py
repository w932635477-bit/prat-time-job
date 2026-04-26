from __future__ import annotations

from career_compass.engine.skill_base import BaseSkill, StepResult
from career_compass.models import Step, StepOption, UserState


class PlanPathSkill(BaseSkill):
    name = "规划路径"
    description = "基于能力地图，推荐变现方向并拆解步骤"
    order = 2

    steps = [
        Step(
            id="urgency",
            question="你现在最急的是几天内见到钱，还是先把口碑做起来？",
            options=[
                StepOption(label="几天内就要见到钱", value="fast"),
                StepOption(label="可以先做口碑", value="reputation"),
                StepOption(label="都可以，看哪个靠谱", value="flexible"),
            ],
        ),
        Step(
            id="comfort_with_people",
            question="你愿不愿意直接和陌生人聊天或打电话？",
            options=[
                StepOption(label="愿意，没问题", value="yes"),
                StepOption(label="可以，但不太自在", value="hesitant"),
                StepOption(label="不愿意，想通过文字", value="text_only"),
            ],
        ),
        Step(
            id="service_format",
            question="你更能接受卖什么？",
            options=[
                StepOption(label="卖服务（咨询/指导/代办）", value="service"),
                StepOption(label="卖信息（清单/报告/推荐）", value="info"),
                StepOption(label="撮合（帮买卖双方牵线）", value="matchmaking"),
            ],
        ),
        Step(
            id="time_budget",
            question="你每周能投入几小时？",
            options=[
                StepOption(label="2小时以内", value="minimal"),
                StepOption(label="2-5小时", value="moderate"),
                StepOption(label="5小时以上", value="committed"),
            ],
        ),
        Step(
            id="free_first",
            question="你能接受首次免费换一个好评吗？",
            options=[
                StepOption(label="可以，先建立信任", value="yes"),
                StepOption(label="不行，必须收费", value="no"),
            ],
        ),
        Step(
            id="wont_do",
            question="你最不愿意做的事情是什么？（说出来我们帮你避开）",
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        answers = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }
        return {
            "skill_type": "plan_path",
            "constraints": answers,
        }
