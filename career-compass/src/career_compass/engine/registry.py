from __future__ import annotations

from career_compass.engine.skill_base import BaseSkill
from career_compass.models import SkillType


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[SkillType, BaseSkill] = {}

    def register(self, skill_type: SkillType, skill: BaseSkill) -> None:
        self._skills[skill_type] = skill

    def get(self, skill_type: SkillType) -> BaseSkill:
        if skill_type not in self._skills:
            raise KeyError(f"Skill not registered: {skill_type}")
        return self._skills[skill_type]

    def list_ordered(self) -> list[tuple[SkillType, BaseSkill]]:
        items = list(self._skills.items())
        items.sort(key=lambda x: x[1].order)
        return items

    def all_types(self) -> list[SkillType]:
        return [t for t, _ in self.list_ordered()]
