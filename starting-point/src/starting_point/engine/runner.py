from __future__ import annotations

from starting_point.engine.registry import SkillRegistry
from starting_point.engine.state import StateManager
from starting_point.models import (
    ChatMessage, ChatResponse, SkillType, UserState, SkillOutput,
    SkillStepResult, PhaseResult,
)


# V2 skill ordering: when a skill completes, advance to the next in this list
V2_SKILL_ORDER = [
    SkillType.ASSESSMENT,
    SkillType.SELF_DISCOVERY,
    SkillType.PRODUCT_PACKAGING,
    SkillType.CUSTOMER_ACQUISITION,
    SkillType.FIRST_DEAL,
    SkillType.GROWTH,
]


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

    def _get_next_skill(self, current: SkillType) -> SkillType | None:
        try:
            idx = V2_SKILL_ORDER.index(current)
        except ValueError:
            return None
        if idx + 1 < len(V2_SKILL_ORDER):
            return V2_SKILL_ORDER[idx + 1]
        return None

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
            output_data, state_updates = await skill.generate_output(state)
            if state_updates:
                state = state.model_copy(update=state_updates)
                await self.state_manager.save_state(state)
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
                output=output_data,
                current_step=state.current_step_index,
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

        # Apply state updates from deliverable (e.g., task_plan_update)
        if result.deliverable and "task_plan_update" in result.deliverable:
            from starting_point.models import TaskPlan
            updated_plan = TaskPlan(**result.deliverable["task_plan_update"])
            state = state.model_copy(update={"task_plan": updated_plan})

        # Handle stuck rescue via LLM
        if result.deliverable and result.deliverable.get("stuck"):
            rescue_result = await self._handle_stuck_rescue(skill, state)
            if rescue_result:
                result = StepResult(
                    next_step=False,
                    confidence_boost=rescue_result,
                )

        if result.next_step:
            state.current_step_index += 1
            state.completed_steps.append(step.id)

        await self.state_manager.save_state(state)

        next_step = skill.get_step(state.current_step_index)

        # Generate task_plan when entering daily_checkin step for the first time
        if next_step and next_step.id == "daily_checkin" and state.task_plan is None:
            output_data, state_updates = await skill.generate_output(state)
            if state_updates:
                state = state.model_copy(update=state_updates)
                await self.state_manager.save_state(state)
        if next_step is None:
            # Current skill completed — generate output, save phase result, advance
            output_data, state_updates = await skill.generate_output(state)
            if state_updates:
                state = state.model_copy(update=state_updates)

            # Save to phase_results
            phase_key = str(skill.order)
            state.phase_results[phase_key] = PhaseResult(
                phase=skill.order, data=output_data,
            )

            # Try to advance to next skill
            next_skill_type = self._get_next_skill(state.current_skill)
            if next_skill_type:
                state.current_skill = next_skill_type
                state.current_step_index = 0
                state.step_results = []
                state.completed_steps = []
                await self.state_manager.save_state(state)

                # Show next skill's first question
                next_skill = self.registry.get(next_skill_type)
                first_step = next_skill.get_step(0)

                overall_progress = (skill.order + 1) / len(V2_SKILL_ORDER)

                return ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content=f'"{skill.name}"完成了。接下来进入"{next_skill.name}"阶段。',
                        confidence_boost=result.confidence_boost,
                    ),
                    progress=overall_progress,
                    deliverable=SkillOutput(
                        skill_type=skill.current_skill if hasattr(skill, 'current_skill') else state.current_skill,
                        data=output_data,
                        summary=f"{skill.name}完成",
                    ),
                    skill_completed=True,
                    output=output_data,
                    current_step=0,
                )

            # All phases completed
            await self.state_manager.save_state(state)
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="恭喜！你已经完成了所有阶段。从今天开始，你不再是一个失业的人——你是一个有自己的小生意的人。",
                    confidence_boost=result.confidence_boost,
                ),
                progress=1.0,
                deliverable=SkillOutput(
                    skill_type=state.current_skill,
                    data=output_data,
                    summary="全部完成",
                ),
                skill_completed=True,
                output=output_data,
                current_step=state.current_step_index,
            )

        progress = state.current_step_index / skill.total_steps
        resp = self._build_step_response(
            next_step, state.current_step_index, skill.total_steps,
            result.confidence_boost,
        )
        # Include task_plan in response when on or entering daily_checkin step
        if state.task_plan and next_step and next_step.id == "daily_checkin":
            resp = resp.model_copy(update={"task_plan": state.task_plan})
        return resp

    async def go_back(
        self, user_id: str, target_step: str,
    ) -> ChatResponse:
        state = await self.state_manager.load_state(user_id)
        if state is None:
            raise ValueError(f"User {user_id} not found")

        # Search current skill first, then all completed skills
        skill, target_index = self._find_step_in_skill(
            state.current_skill, target_step,
        )
        if skill is None:
            for skill_type in V2_SKILL_ORDER:
                if skill_type == state.current_skill:
                    continue
                skill, target_index = self._find_step_in_skill(
                    skill_type, target_step,
                )
                if skill is not None:
                    # Rewind to earlier skill
                    state.current_skill = skill_type
                    state.step_results = []
                    state.completed_steps = []
                    break

        if skill is None:
            raise ValueError(f"Step {target_step} not found")

        state.current_step_index = target_index
        state.completed_steps = [s.id for s in skill.steps[:target_index]]
        state.step_results = state.step_results[:target_index]
        await self.state_manager.save_state(state)

        step = skill.get_step(target_index)
        progress = target_index / skill.total_steps
        return self._build_step_response(step, target_index, skill.total_steps)

    def _find_step_in_skill(
        self, skill_type: SkillType, target_step: str,
    ) -> tuple[object | None, int | None]:
        skill = self.registry.get(skill_type)
        for i, s in enumerate(skill.steps):
            if s.id == target_step:
                return skill, i
        return None, None

    async def _handle_stuck_rescue(self, skill, state) -> str | None:
        if not hasattr(skill, "generate_rescue"):
            return None
        if state.task_plan is None:
            return None
        current_idx = state.task_plan.current_day - 1
        if current_idx >= len(state.task_plan.days):
            return None
        task = state.task_plan.days[current_idx]
        rescue_data = await skill.generate_rescue(
            day=task.day,
            task=task.task,
            platform=task.platform,
            stuck_reason=task.stuck_reason or "未说明原因",
            completed_days=current_idx,
        )
        if rescue_data is None:
            return None
        parts = []
        if rescue_data.get("encouragement"):
            parts.append(rescue_data["encouragement"])
        if rescue_data.get("diagnosis"):
            parts.append(f"分析：{rescue_data['diagnosis']}")
        for i, s in enumerate(rescue_data.get("steps", []), 1):
            parts.append(f"{i}. {s}")
        if rescue_data.get("alternative"):
            parts.append(f"替代方案：{rescue_data['alternative']}")
        return "\n".join(parts)

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
            current_step=index,
        )
