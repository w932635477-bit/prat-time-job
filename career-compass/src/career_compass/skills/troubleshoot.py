from __future__ import annotations

from career_compass.engine.skill_base import BaseSkill, StepResult
from career_compass.models import Step, StepOption, UserState


class TroubleshootSkill(BaseSkill):
    name = "卡住了"
    description = "你卡在哪了？帮你解决问题"
    order = 4

    steps = [
        Step(
            id="problem_type",
            question="你遇到了什么问题？",
            options=[
                StepOption(label="不知道怎么做", value="dont_know_how"),
                StepOption(label="做了但效果不好", value="not_working"),
                StepOption(label="有技术困难", value="technical"),
                StepOption(label="有心理障碍", value="psychological"),
            ],
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        return {"skill_type": "troubleshoot", "status": "resolved"}
