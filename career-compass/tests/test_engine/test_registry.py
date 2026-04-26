from career_compass.engine.registry import SkillRegistry
from career_compass.engine.skill_base import BaseSkill, StepResult
from career_compass.models import Step, SkillType, UserState


class DummySkill(BaseSkill):
    name = "Dummy"
    description = "test"
    order = 1
    steps = [Step(id="s1", question="Q")]

    def process_answer(self, step_id, answer, state):
        return StepResult()

    def generate_output(self, state):
        return {}


def test_registry_registers_skill():
    registry = SkillRegistry()
    skill = DummySkill()
    registry.register(SkillType.SELF_DISCOVERY, skill)
    assert registry.get(SkillType.SELF_DISCOVERY) is skill


def test_registry_lists_ordered_skills():
    registry = SkillRegistry()
    registry.register(SkillType.SELF_DISCOVERY, DummySkill())
    registry.register(SkillType.PLAN_PATH, DummySkill())
    ordered = registry.list_ordered()
    assert len(ordered) == 2


def test_registry_raises_on_missing():
    registry = SkillRegistry()
    try:
        registry.get(SkillType.TROUBLESHOOT)
        assert False, "Should have raised"
    except KeyError:
        pass
