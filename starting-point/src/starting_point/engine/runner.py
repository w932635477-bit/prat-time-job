from __future__ import annotations

from starting_point.engine.registry import SkillRegistry
from starting_point.engine.state import StateManager
from starting_point.models import (
    ChatMessage, ChatResponse, SkillType, UserState, SkillOutput,
    SkillStepResult,
)


class SkillRunner:
    def __init__(
        self,
        registry: SkillRegistry,
        state_manager: StateManager,
        llm_client: object | None = None,
    ) -> None:
        self.registry = registry
        self.state_manager = state_manager
        self.llm_client = llm_client

    async def _get_or_create_state(self, user_id: str) -> UserState:
        state = await self.state_manager.load_state(user_id)
        if state is None:
            state = UserState(user_id=user_id)
            await self.state_manager.save_state(state)
        return state

    async def process_message(
        self,
        user_id: str,
        message: str,
        selected_option: str | None,
    ) -> ChatResponse:
        state = await self._get_or_create_state(user_id)
        skill = self.registry.get(state.current_skill)

        step = skill.get_step(state.current_step_index)

        # First interaction: show first question and mark started
        if not state.started:
            state.started = True
            await self.state_manager.save_state(state)
            return self._build_step_response(step, 0, skill.total_steps)

        if step is None:
            output_data = await skill.generate_output(state)
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="你已完成这个环节！",
                ),
                progress=1.0,
                deliverable=SkillOutput(
                    skill_type=state.current_skill,
                    data=output_data,
                    summary="环节完成",
                ),
                skill_completed=True,
            )

        # Record answer
        result_record = SkillStepResult(
            step_id=step.id,
            answer=message,
            selected_option=selected_option,
            free_text=message if selected_option is None else None,
        )
        state.step_results.append(result_record)

        result = skill.process_answer(step.id, message, state)
        if result.next_step:
            state.current_step_index += 1
            state.completed_steps.append(step.id)

        await self.state_manager.save_state(state)

        next_step = skill.get_step(state.current_step_index)
        if next_step is None:
            output_data = await skill.generate_output(state)
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="你已完成这个环节！",
                    confidence_boost=result.confidence_boost,
                ),
                progress=1.0,
                deliverable=SkillOutput(
                    skill_type=state.current_skill,
                    data=output_data,
                    summary="环节完成",
                ),
                skill_completed=True,
            )

        progress = state.current_step_index / skill.total_steps
        return self._build_step_response(
            next_step, state.current_step_index, skill.total_steps,
            result.confidence_boost,
        )

    async def go_back(
        self, user_id: str, target_step: str,
    ) -> ChatResponse:
        state = await self.state_manager.load_state(user_id)
        if state is None:
            raise ValueError(f"User {user_id} not found")

        skill = self.registry.get(state.current_skill)
        target_index = None
        for i, s in enumerate(skill.steps):
            if s.id == target_step:
                target_index = i
                break

        if target_index is None:
            raise ValueError(f"Step {target_step} not found")

        state.step_results = state.step_results[:target_index]
        state.current_step_index = target_index
        state.completed_steps = [s.id for s in skill.steps[:target_index]]
        await self.state_manager.save_state(state)

        step = skill.get_step(target_index)
        progress = target_index / skill.total_steps
        return self._build_step_response(step, target_index, skill.total_steps)

    def _build_step_response(
        self,
        step,
        index: int,
        total: int,
        confidence_boost: str | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=step.question,
                options=step.options,
                allow_free_text=step.allow_free_text,
                step_id=step.id,
                confidence_boost=confidence_boost,
            ),
            progress=index / total if total > 0 else 0.0,
        )
