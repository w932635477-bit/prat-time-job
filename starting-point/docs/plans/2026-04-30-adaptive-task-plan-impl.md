# 自由行业输入 + 自适应任务计划 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two product issues: (1) add free-text "other" option to industry selection, (2) transform Phase 3 from 3-step Q&A into a persistent 14-30 day task check-in with AI rescue.

**Architecture:** Add "其他" option to SelfDiscovery industry step. Transform CustomerAcquisitionSkill into a 4-step skill where step 4 is a repeating daily_checkin loop. Add TaskDay/TaskPlan models, stuck rescue prompt, and check-in UI.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, vanilla JS (ES modules), pytest

---

### Task 1: Add "其他" option to industry step

**Files:**
- Modify: `src/starting_point/skills/self_discovery.py:20-31`
- Test: `tests/test_skills/test_self_discovery.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_self_discovery.py`:

```python
def test_industry_step_has_other_option():
    skill = SelfDiscoverySkill()
    step = skill.get_step(0)
    values = [o.value for o in step.options]
    assert "other" in values
    other = next(o for o in step.options if o.value == "other")
    assert "其他" in other.label or "手动" in other.label
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_self_discovery.py::test_industry_step_has_other_option -v`
Expected: FAIL — "other" not in values

**Step 3: Write minimal implementation**

In `src/starting_point/skills/self_discovery.py`, add one more StepOption at line 29 (after logistics):

```python
                StepOption(label="物流/运输", value="logistics"),
                StepOption(label="其他（手动输入）", value="other"),
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_self_discovery.py::test_industry_step_has_other_option -v`
Expected: PASS

**Step 5: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All existing tests pass (new option is additive, no breaking changes)

**Step 6: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add src/starting_point/skills/self_discovery.py tests/test_skills/test_self_discovery.py && git commit -m "feat: add 'other' free-text option to industry selection step"
```

---

### Task 2: Add "other" option frontend handler

**Files:**
- Modify: `static/js/app.js:59-80`

**Step 1: Write the test (manual browser verification)**

This is a frontend-only change. We will verify manually after implementation.

**Step 2: Implement "other" option handler in app.js**

In `static/js/app.js`, modify the `renderOptions` function. After the `forEach` loop that creates buttons (line 63-77), add logic to detect "other" option clicks:

Replace the existing `renderOptions` function (lines 59-80) with:

```javascript
function renderOptions(options, onSelect) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--options fade-in';
  let busy = false;
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => {
      if (busy) return;
      if (opt.value === 'other') {
        busy = true;
        row.querySelectorAll('.option-btn').forEach(b => b.disabled = true);
        btn.classList.add('option-btn--selected');
        showOtherInput(row, onSelect);
        return;
      }
      busy = true;
      row.querySelectorAll('.option-btn').forEach(b => {
        b.classList.remove('option-btn--selected');
        b.disabled = true;
      });
      btn.classList.add('option-btn--selected');
      onSelect(opt);
    });
    row.appendChild(btn);
  });
  return row;
}

function showOtherInput(optionsRow, onSelect) {
  const wrapper = document.createElement('div');
  wrapper.className = 'other-input-wrapper fade-in';
  wrapper.style.cssText = 'display:flex;gap:8px;margin-top:8px;padding:0 4px;';

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = '请输入你的行业...';
  input.className = 'other-input';
  input.style.cssText = 'flex:1;padding:10px 14px;border:1px solid #e0e0e0;border-radius:10px;font-size:15px;outline:none;';
  input.setAttribute('aria-label', '输入你的行业');

  const confirmBtn = document.createElement('button');
  confirmBtn.textContent = '确认';
  confirmBtn.className = 'option-btn';
  confirmBtn.style.cssText = 'min-width:60px;';
  confirmBtn.addEventListener('click', () => {
    const val = input.value.trim();
    if (!val) {
      input.style.borderColor = '#ff4444';
      input.placeholder = '请先输入你的行业';
      return;
    }
    confirmBtn.disabled = true;
    input.disabled = true;
    onSelect({ label: val, value: val });
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') confirmBtn.click();
  });

  wrapper.appendChild(input);
  wrapper.appendChild(confirmBtn);
  optionsRow.appendChild(wrapper);

  input.focus();
}
```

**Step 3: Run dev server and verify manually**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && --noproxy localhost curl -s http://localhost:8000/ | head -5`

Open browser to `http://localhost:8000/`, navigate to Phase 1 step 0, verify:
- 6 buttons appear (5 industries + "其他（手动输入）")
- Clicking "其他" shows an input field + confirm button
- Typing an industry and confirming sends it as the answer
- Clicking any other option works as before

**Step 4: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add static/js/app.js && git commit -m "feat: add free-text input UI for 'other' industry option"
```

---

### Task 3: Add TaskDay and TaskPlan models

**Files:**
- Modify: `src/starting_point/models.py` (add after DailyTaskPlan class at ~line 83)
- Test: `tests/test_skills/test_other_skills.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_other_skills.py`:

```python
def test_task_day_model_defaults():
    from starting_point.models import TaskDay
    td = TaskDay(day=1, task="发帖子", platform="小红书")
    assert td.status == "pending"
    assert td.stuck_reason is None
    assert td.rescue_advice is None
    assert td.estimated_time == "30分钟"


def test_task_plan_model():
    from starting_point.models import TaskPlan, TaskDay
    plan = TaskPlan(
        total_days=14,
        current_day=1,
        days=[TaskDay(day=1, task="测试", platform="小红书")],
        platform="小红书",
    )
    assert plan.status == "active"
    assert len(plan.days) == 1


def test_user_state_has_task_plan_field():
    from starting_point.models import UserState, TaskPlan
    state = UserState(user_id="test")
    assert state.task_plan is None
    state2 = UserState(user_id="test", task_plan=TaskPlan(total_days=20))
    assert state2.task_plan.total_days == 20
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_task_day_model_defaults -v`
Expected: FAIL — ImportError for TaskDay

**Step 3: Write minimal implementation**

In `src/starting_point/models.py`, add after the `DailyTaskPlan` class (after line 83):

```python
class TaskDay(BaseModel):
    day: int
    task: str
    platform: str
    estimated_time: str = "30分钟"
    why: str = ""
    success_signal: str = ""
    status: str = "pending"          # pending | done | stuck | skipped
    stuck_reason: str | None = None
    rescue_advice: str | None = None
    completed_at: datetime | None = None


class TaskPlan(BaseModel):
    total_days: int = 14
    current_day: int = 1
    days: list[TaskDay] = Field(default_factory=list)
    platform: str = ""
    status: str = "active"  # active | completed | abandoned
```

Also add `task_plan` field to `UserState` class (after `content_plan` field at ~line 166):

```python
    task_plan: TaskPlan | None = None
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_task_day_model_defaults tests/test_skills/test_other_skills.py::test_task_plan_model tests/test_skills/test_other_skills.py::test_user_state_has_task_plan_field -v`
Expected: All 3 PASS

**Step 5: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All tests pass (new fields have defaults, no breaking changes)

**Step 6: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add src/starting_point/models.py tests/test_skills/test_other_skills.py && git commit -m "feat: add TaskDay and TaskPlan models for adaptive task plan"
```

---

### Task 4: Add stuck rescue prompt template

**Files:**
- Modify: `src/starting_point/llm/prompts.py:214-235` (add template after DAILY_TASKS_TEMPLATE)
- Test: `tests/test_skills/test_other_skills.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_other_skills.py`:

```python
def test_stuck_rescue_prompt_contains_task_info():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_stuck_rescue_prompt(
        day=5,
        task="在小红书发一篇装修避坑笔记",
        platform="小红书",
        stuck_reason="不知道怎么拍照，手机拍出来效果很差",
        completed_days=4,
    )
    assert "小红书" in prompt
    assert "装修避坑" in prompt
    assert "拍照" in prompt
    assert "建议" in prompt or "advice" in prompt.lower()


def test_adaptive_daily_tasks_prompt_uses_suggested_days():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_daily_tasks_prompt(
        platform="小红书",
        service_name="装修避坑咨询",
        asset_map="瓷砖选购经验",
        market_signals="有人主动咨询",
        digital_literacy="intermediate",
        time_commitment="1-3h",
        suggested_days=20,
    )
    assert "20" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_stuck_rescue_prompt_contains_task_info -v`
Expected: FAIL — AttributeError: 'PromptBuilder' has no attribute 'build_stuck_rescue_prompt'

**Step 3: Write minimal implementation**

In `src/starting_point/llm/prompts.py`, add after `DAILY_TASKS_TEMPLATE` (after line 235):

```python
    STUCK_RESCUE_TEMPLATE = """你是启点的行动教练。用户在第{day}天的任务中卡住了，请给出具体、可操作的建议。

当前任务：{task}
平台：{platform}
卡住的原因：{stuck_reason}
已坚持天数：{completed_days}天

规则：
- 不要说"加油"，给具体步骤
- 如果是技术问题，给工具名和操作步骤
- 如果是心理问题，给降低门槛的替代方案
- 建议必须能在15分钟内执行
- 用大白话，不要术语

输出JSON格式：
{{"encouragement": "一句话认可用户的坚持", "diagnosis": "为什么卡住了（一句话）", "steps": ["具体步骤1", "具体步骤2", "具体步骤3"], "alternative": "如果还是不行，替代方案是什么", "next_action": "解决后继续做什么"}}"""
```

Update `build_daily_tasks_prompt` method to accept `suggested_days`:

```python
    def build_daily_tasks_prompt(
        self, platform: str, service_name: str, asset_map: str,
        market_signals: str, digital_literacy: str, time_commitment: str,
        suggested_days: int = 14,
    ) -> str:
        template = self.DAILY_TASKS_TEMPLATE.replace("7天", f"{suggested_days}天").replace("第1-2天", "前3天").replace("一个7天逐日行动计划", f"一个{suggested_days}天逐日行动计划")
        return template.format(
            platform=platform, service_name=service_name,
            asset_map=asset_map, market_signals=market_signals,
            digital_literacy=digital_literacy, time_commitment=time_commitment,
        )
```

Add the `build_stuck_rescue_prompt` method:

```python
    def build_stuck_rescue_prompt(
        self, day: int, task: str, platform: str,
        stuck_reason: str, completed_days: int,
    ) -> str:
        return self.STUCK_RESCUE_TEMPLATE.format(
            day=day, task=task, platform=platform,
            stuck_reason=stuck_reason, completed_days=completed_days,
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_stuck_rescue_prompt_contains_task_info tests/test_skills/test_other_skills.py::test_adaptive_daily_tasks_prompt_uses_suggested_days -v`
Expected: All PASS

**Step 5: Update existing test that checks for "7" in prompt**

The existing test `test_daily_tasks_prompt_contains_key_fields` checks `assert "7" in prompt`. Since we changed the template to use `{suggested_days}天`, the default is now 14. Update the test in `tests/test_skills/test_other_skills.py`:

```python
def test_daily_tasks_prompt_contains_key_fields():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_daily_tasks_prompt(
        platform="小红书",
        service_name="装修避坑咨询",
        asset_map="瓷砖选购经验",
        market_signals="有人主动咨询",
        digital_literacy="intermediate",
        time_commitment="1-3h",
    )
    assert "小红书" in prompt
    assert "14" in prompt
    assert "任务" in prompt or "task" in prompt.lower()
```

**Step 6: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All tests pass

**Step 7: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add src/starting_point/llm/prompts.py tests/test_skills/test_other_skills.py && git commit -m "feat: add stuck rescue prompt and adaptive day count to daily tasks template"
```

---

### Task 5: Add daily_checkin step to CustomerAcquisitionSkill

**Files:**
- Modify: `src/starting_point/skills/customer_acquisition.py`
- Test: `tests/test_skills/test_other_skills.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_other_skills.py`:

```python
def test_customer_acquisition_has_daily_checkin_step():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()
    step = skill.get_step(3)
    assert step is not None
    assert step.id == "daily_checkin"


def test_customer_acquisition_total_steps_is_4():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()
    assert skill.total_steps == 4


def test_process_checkin_done_updates_plan():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, TaskPlan, TaskDay, SkillStepResult
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    state.task_plan = TaskPlan(
        total_days=3,
        current_day=1,
        days=[
            TaskDay(day=1, task="发帖", platform="小红书"),
            TaskDay(day=2, task="回复", platform="小红书"),
            TaskDay(day=3, task="优化", platform="小红书"),
        ],
        platform="小红书",
    )
    result = skill.process_answer("daily_checkin", "完成了", state)
    assert result.next_step is True


def test_process_checkin_stuck_triggers_rescue():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, TaskPlan, TaskDay, StepResult
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    state.task_plan = TaskPlan(
        total_days=3,
        current_day=1,
        days=[TaskDay(day=1, task="发帖", platform="小红书")],
        platform="小红书",
    )
    result = skill.process_answer("daily_checkin", "卡住了：不知道怎么拍照", state)
    assert result.confidence_boost is not None or result.deliverable is not None
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_customer_acquisition_has_daily_checkin_step -v`
Expected: FAIL — step 3 returns None

**Step 3: Rewrite CustomerAcquisitionSkill**

Replace the entire `src/starting_point/skills/customer_acquisition.py`:

```python
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

        # Determine adaptive day count
        suggested_days = self._calculate_suggested_days(
            digital_literacy or "intermediate",
            time_commitment or "1-3h",
        )

        if self._llm is None:
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "tasks": [],
                "suggested_days": suggested_days,
            }, {}

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

        from starting_point.models import TaskPlan, TaskDay
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
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_other_skills.py::test_customer_acquisition_has_daily_checkin_step tests/test_skills/test_other_skills.py::test_customer_acquisition_total_steps_is_4 tests/test_skills/test_other_skills.py::test_process_checkin_done_updates_plan tests/test_skills/test_other_skills.py::test_process_checkin_stuck_triggers_rescue -v`
Expected: All PASS

**Step 5: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All tests pass

**Step 6: Update PHASES step count in frontend**

In `static/js/phases/index.js`, change steps for customer_acquisition from 3 to 4:

```javascript
  { id: 'customer_acquisition', name: '找到客户', steps: 4 },
```

**Step 7: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add src/starting_point/skills/customer_acquisition.py tests/test_skills/test_other_skills.py static/js/phases/index.js && git commit -m "feat: transform Phase 3 into adaptive task plan with daily check-in"
```

---

### Task 6: Update SkillRunner to handle daily_checkin loop

**Files:**
- Modify: `src/starting_point/engine/runner.py`

**Step 1: Understand the problem**

The current runner (line 87-101) records an answer, calls `process_answer`, then advances `current_step_index` by 1. When `next_step=False`, it stays on the same step. This works for checkin: when `result.next_step=False`, the runner shows the same step again. When all tasks are done, `next_step=True` triggers skill completion.

However, we need to handle the `deliverable` from `_process_checkin` to update `state.task_plan`. The runner needs to apply these state updates when `result.deliverable` contains `task_plan_update`.

**Step 2: Modify the runner to handle deliverable state updates**

In `src/starting_point/engine/runner.py`, modify the section after `result = skill.process_answer(...)` (around line 96-101). Change:

```python
        result = skill.process_answer(step.id, message, state)
        if result.next_step:
            state.current_step_index += 1
            state.completed_steps.append(step.id)
```

To:

```python
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
```

Add the helper method to the SkillRunner class:

```python
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
        steps = rescue_data.get("steps", [])
        alternative = rescue_data.get("alternative", "")
        parts = []
        if rescue_data.get("encouragement"):
            parts.append(rescue_data["encouragement"])
        if rescue_data.get("diagnosis"):
            parts.append(f"分析：{rescue_data['diagnosis']}")
        for i, s in enumerate(steps, 1):
            parts.append(f"{i}. {s}")
        if alternative:
            parts.append(f"替代方案：{alternative}")
        return "\n".join(parts)
```

**Step 3: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add src/starting_point/engine/runner.py && git commit -m "feat: handle daily_checkin loop and stuck rescue in SkillRunner"
```

---

### Task 7: Build check-in UI for customer-acquisition phase

**Files:**
- Rewrite: `static/js/phases/customer-acquisition.js`

**Step 1: Understand the flow**

When the user is on step 3 (daily_checkin), the backend sends:
- `message.options`: `[{label: "完成了", value: "done"}, {label: "卡住了，需要帮助", value: "stuck"}]`
- `message.confidence_boost`: contains progress text or rescue advice

The frontend needs to:
1. Show today's task card from `task_plan`
2. Handle "done" → mark complete, show progress
3. Handle "stuck" → show text input for reason, submit
4. Show rescue advice when returned
5. When all days complete, trigger phase completion

**Step 2: Rewrite customer-acquisition.js**

Replace the entire file:

```javascript
// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: Adaptive Task Plan with daily check-in

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

  const platform = data.platform || '小红书';
  const tasks = data.tasks || [];
  const suggestedDays = data.suggested_days || 14;

  const titleCard = document.createElement('div');
  titleCard.className = 'output-card fade-in';
  titleCard.innerHTML = `
    <div class="output-card__title">${suggestedDays}天行动计划</div>
    <div class="output-card__subtitle">平台: ${esc(platform)} · 每天30分钟内</div>
  `;
  wrapper.appendChild(titleCard);

  if (tasks.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'output-card fade-in';
    empty.innerHTML = '<div class="output-card__value">任务生成中，请稍后刷新</div>';
    wrapper.appendChild(empty);
    return wrapper;
  }

  tasks.forEach(task => {
    wrapper.appendChild(renderTaskCard(task));
  });

  return wrapper;
}

function renderTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'task-card fade-in';

  const dayLabel = task.day === 1 ? '今天' : `第${task.day}天`;
  const checked = isTaskCompleted(task.day);

  card.innerHTML = `
    <div class="task-card__header">
      <label class="task-card__checkbox">
        <input type="checkbox" data-day="${task.day}" ${checked ? 'checked' : ''} />
        <span class="task-card__day">${esc(dayLabel)}</span>
      </label>
      <span class="task-card__time">${esc(task.estimated_time || '30分钟')}</span>
    </div>
    <div class="task-card__task">${esc(task.task)}</div>
    <div class="task-card__meta">
      <span class="task-card__platform">${esc(task.platform)}</span>
    </div>
    <div class="task-card__why">${esc(task.why)}</div>
    <div class="task-card__signal">成功信号: ${esc(task.success_signal)}</div>
  `;

  const checkbox = card.querySelector('input[type="checkbox"]');
  checkbox.addEventListener('change', () => {
    toggleTaskCompleted(task.day);
    if (checkbox.checked) {
      card.classList.add('task-card--done');
    } else {
      card.classList.remove('task-card--done');
    }
  });

  if (checked) {
    card.classList.add('task-card--done');
  }

  return card;
}

const STORAGE_KEY = 'starting_point_completed_tasks';

function isTaskCompleted(day) {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return !!saved[day];
  } catch { return false; }
}

function toggleTaskCompleted(day) {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch {}
  saved[day] = !saved[day];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}

export function getSummary(data) {
  const tasks = data.tasks || [];
  const suggestedDays = data.suggested_days || 14;
  const done = tasks.filter(t => isTaskCompleted(t.day)).length;
  return `${suggestedDays}天行动计划 (${done}/${tasks.length} 完成)`;
}

export function renderCheckinCard(taskDay, currentDay, totalDays) {
  const card = document.createElement('div');
  card.className = 'checkin-card fade-in';

  const progressPct = Math.round((currentDay / totalDays) * 100);

  card.innerHTML = `
    <div class="checkin-card__progress">
      <div class="checkin-card__progress-bar">
        <div class="checkin-card__progress-fill" style="width:${progressPct}%"></div>
      </div>
      <span class="checkin-card__progress-text">第${currentDay}/${totalDays}天</span>
    </div>
    <div class="checkin-card__task-title">${esc(taskDay.task)}</div>
    <div class="checkin-card__meta">
      <span class="checkin-card__platform">${esc(taskDay.platform)}</span>
      <span class="checkin-card__time">${esc(taskDay.estimated_time || '30分钟')}</span>
    </div>
    <div class="checkin-card__why">${esc(taskDay.why)}</div>
    <div class="checkin-card__signal">成功信号: ${esc(taskDay.success_signal)}</div>
  `;

  return card;
}

export function renderRescueAdvice(advice) {
  const card = document.createElement('div');
  card.className = 'rescue-card fade-in';
  card.innerHTML = `
    <div class="rescue-card__title">帮你分析一下</div>
    <div class="rescue-card__advice">${esc(advice)}</div>
  `;
  return card;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
```

**Step 3: Update app.js to handle daily_checkin rendering**

In `static/js/app.js`, modify `handleResponse` function. After the section that renders AI bubble and options (around line 211-222), add checkin card rendering:

After the block:
```javascript
  if (response.message) {
    const content = response.message.content || response.message.question || '';
    messages.appendChild(renderBubbleAi(content));
    ...
```

Add before the closing `}` of the `if (response.message)` block:

```javascript
    // Render checkin card when on daily_checkin step
    if (response.message.step_id === 'daily_checkin' && response.output) {
      const taskPlan = response.output.task_plan || response.output;
      if (taskPlan.days && taskPlan.current_day) {
        const currentIdx = taskPlan.current_day - 1;
        if (currentIdx < taskPlan.days.length) {
          const renderer = await getRenderer('customer-acquisition');
          const checkinCard = renderer.renderCheckinCard(
            taskPlan.days[currentIdx],
            taskPlan.current_day,
            taskPlan.total_days,
          );
          messages.appendChild(checkinCard);
        }
      }
    }
```

**Step 4: Run dev server and verify**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m uvicorn starting_point.main:app --reload --port 8000`

Open browser and test:
1. Navigate through phases until Phase 3
2. Select platform, confirm plan
3. See daily task card with "完成了" and "卡住了" buttons
4. Click "卡住了" → enter reason → see rescue advice
5. Click "完成了" → see progress, next day appears

**Step 5: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add static/js/phases/customer-acquisition.js static/js/app.js && git commit -m "feat: build daily check-in UI with progress bar and rescue display"
```

---

### Task 8: Add CSS styles for check-in cards

**Files:**
- Modify: `static/css/design-system.css`

**Step 1: Add styles**

Append to `static/css/design-system.css`:

```css
/* --- Checkin Card --- */
.checkin-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px;
  margin: 8px 0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.checkin-card__progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.checkin-card__progress-bar {
  flex: 1;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
}
.checkin-card__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ff6b35, #ff9a56);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.checkin-card__progress-text {
  font-size: 13px;
  color: #888;
  white-space: nowrap;
}
.checkin-card__task-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}
.checkin-card__meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}
.checkin-card__why {
  font-size: 14px;
  color: #555;
  margin-bottom: 6px;
}
.checkin-card__signal {
  font-size: 13px;
  color: #ff6b35;
}

/* --- Rescue Card --- */
.rescue-card {
  background: #fff8f0;
  border: 1px solid #ffe0c0;
  border-radius: 14px;
  padding: 18px;
  margin: 8px 0;
}
.rescue-card__title {
  font-size: 15px;
  font-weight: 600;
  color: #ff6b35;
  margin-bottom: 10px;
}
.rescue-card__advice {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  white-space: pre-line;
}

/* --- Other Input --- */
.other-input-wrapper input:focus {
  border-color: #ff6b35;
  box-shadow: 0 0 0 2px rgba(255,107,53,0.15);
}
```

**Step 2: Run dev server and verify visually**

Open browser and verify:
- Checkin card has progress bar, task info, and clean layout
- Rescue card has warm background with advice
- Other input has focus ring

**Step 3: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add static/css/design-system.css && git commit -m "feat: add CSS styles for checkin cards, rescue display, and other input"
```

---

### Task 9: Integration test and final verification

**Files:**
- Test: `tests/test_skills/test_other_skills.py`

**Step 1: Write integration test**

Add to `tests/test_skills/test_other_skills.py`:

```python
@pytest.mark.asyncio
async def test_customer_acquisition_generates_adaptive_plan():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    tasks = [{"day": i, "task": f"任务{i}", "platform": "小红书", "estimated_time": "30分钟", "why": "原因", "success_signal": "信号"} for i in range(1, 15)]
    llm.chat.return_value = json.dumps({"tasks": tasks})

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test")
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu", selected_option="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert "tasks" in output
    assert output["suggested_days"] == 14
    assert "task_plan" in updates
    assert updates["task_plan"].total_days == 14
    assert len(updates["task_plan"].days) == 14


@pytest.mark.asyncio
async def test_customer_acquisition_beginner_gets_more_days():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, UserAssessment, SkillStepResult

    llm = AsyncMock()
    tasks = [{"day": i, "task": f"任务{i}", "platform": "小红书", "estimated_time": "30分钟", "why": "原因", "success_signal": "信号"} for i in range(1, 22)]
    llm.chat.return_value = json.dumps({"tasks": tasks})

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test", assessment=UserAssessment(digital_literacy="beginner", time_commitment="1h"))
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert output["suggested_days"] >= 21


@pytest.mark.asyncio
async def test_rescue_generates_advice():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill

    llm = AsyncMock()
    llm.chat.return_value = '{"encouragement": "坚持到了第3天很棒", "diagnosis": "拍照技巧不够", "steps": ["用自然光", "拍3张选最好的"], "alternative": "先发文字笔记", "next_action": "完成后继续第4天"}'

    skill = CustomerAcquisitionSkill(llm_client=llm)
    result = await skill.generate_rescue(
        day=3, task="在小红书发一篇装修避坑笔记", platform="小红书",
        stuck_reason="不知道怎么拍照", completed_days=2,
    )
    assert result is not None
    assert len(result.get("steps", [])) > 0
    assert result.get("diagnosis") is not None


def test_calculate_suggested_days():
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    skill = CustomerAcquisitionSkill()

    # Beginner + low time = max days
    assert skill._calculate_suggested_days("beginner", "1h") == 28

    # Advanced + lots of time = min days
    assert skill._calculate_suggested_days("advanced", "3-5h") == 14

    # Intermediate = middle
    assert skill._calculate_suggested_days("intermediate", "1-3h") == 14
```

**Step 2: Run all tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: All tests pass

**Step 3: Run dev server and do end-to-end manual test**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m uvicorn starting_point.main:app --reload --port 8000`

Manual verification checklist:
- [ ] Phase 1 step 0: 6 industry options visible, "其他" works with text input
- [ ] Phase 3: Platform selection works
- [ ] Phase 3: Plan generation shows day count (14-30)
- [ ] Phase 3: Daily check-in card shows with progress bar
- [ ] Phase 3: "完成了" marks task done, advances day
- [ ] Phase 3: "卡住了" shows reason input, AI rescue advice appears
- [ ] Phase 3: All days complete → phase advances

**Step 4: Final commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && git add tests/test_skills/test_other_skills.py && git commit -m "test: add integration tests for adaptive task plan and rescue"
```
