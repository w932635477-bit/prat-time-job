from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from starting_point.models import Step, UserState


@dataclass
class StepResult:
    next_step: bool = True
    confidence_boost: str | None = None
    deliverable: dict | None = None


class BaseSkill(ABC):
    name: str
    description: str
    order: int
    steps: list[Step]

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def get_step(self, index: int) -> Step | None:
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None

    def is_complete(self, step_index: int) -> bool:
        return step_index >= len(self.steps)

    @abstractmethod
    def process_answer(
        self,
        step_id: str,
        answer: str,
        state: UserState,
    ) -> StepResult:
        ...

    @abstractmethod
    async def generate_output(self, state: UserState) -> dict:
        ...
