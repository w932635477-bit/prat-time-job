from __future__ import annotations

from career_compass.engine.skill_base import BaseSkill, StepResult
from career_compass.models import Step, StepOption, UserState


class TakeActionSkill(BaseSkill):
    name = "开张行动"
    description = "生成首发文案，帮你上线（简化版）"
    order = 3

    steps = [
        Step(
            id="platform",
            question="你想先在哪个平台发布？",
            options=[
                StepOption(label="闲鱼", value="xianyu"),
                StepOption(label="小红书", value="xiaohongshu"),
                StepOption(label="朋友圈", value="wechat"),
            ],
        ),
        Step(
            id="confirm_launch",
            question="文案已生成！你准备发布吗？如果有想修改的地方，告诉我。",
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        return {"skill_type": "take_action", "status": "content_generated"}
