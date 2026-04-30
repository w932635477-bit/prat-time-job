# 7-Day Daily Task Cards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 30-day content plan with 7-day daily task cards that give users one concrete action per day.

**Architecture:** Backend generates 7 task cards via LLM, frontend renders them as checkable cards with localStorage persistence.

**Tech Stack:** Python 3.12, FastAPI, vanilla JS, localStorage

---

### Task 1: Add DailyTask and DailyTaskPlan models

**Files:**
- Modify: `src/starting_point/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

Add to `tests/test_models.py`:

```python
def test_daily_task_creation():
    from starting_point.models import DailyTask
    task = DailyTask(
        day=1, task="在闲鱼发一条咨询帖子", platform="闲鱼",
        estimated_time="20分钟", why="你上次说的瓷砖经验正是业主需要的",
        success_signal="有人来问",
    )
    assert task.day == 1
    assert task.platform == "闲鱼"


def test_daily_task_plan_creation():
    from starting_point.models import DailyTask, DailyTaskPlan
    tasks = [DailyTask(day=1, task="test", platform="x", estimated_time="10分钟", why="reason", success_signal="sig")]
    plan = DailyTaskPlan(tasks=tasks, platform="小红书")
    assert len(plan.tasks) == 1
    assert plan.platform == "小红书"
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest tests/test_models.py::test_daily_task_creation -v`
Expected: FAIL (DailyTask doesn't exist)

**Step 3: Add models**

In `src/starting_point/models.py`, add after `MarketSignals` class:

```python
class DailyTask(BaseModel):
    day: int
    task: str
    platform: str
    estimated_time: str = "30分钟"
    why: str = ""
    success_signal: str = ""


class DailyTaskPlan(BaseModel):
    tasks: list[DailyTask] = Field(default_factory=list)
    platform: str = ""
```

**Step 4: Run tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest tests/test_models.py -v`
Expected: All PASS

**Step 5: Run full suite**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest -v`

**Step 6: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add src/starting_point/models.py tests/test_models.py
git commit -m "feat: add DailyTask and DailyTaskPlan models"
```

---

### Task 2: Add DAILY_TASKS_TEMPLATE prompt

**Files:**
- Modify: `src/starting_point/llm/prompts.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_other_skills.py` (or create a new test file if preferred):

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
    assert "7" in prompt
    assert "task" in prompt.lower() or "任务" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest tests/test_skills/test_other_skills.py::test_daily_tasks_prompt_contains_key_fields -v`
Expected: FAIL (build_daily_tasks_prompt doesn't exist)

**Step 3: Add template and builder method**

In `src/starting_point/llm/prompts.py`, add this template string after the existing templates:

```python
DAILY_TASKS_TEMPLATE = """你是启点的行动教练。为用户生成一个7天逐日行动计划，每天一个具体任务。

平台：{platform}
服务产品：{service_name}
用户的核心资产：{asset_map}
市场信号：{market_signals}
数字能力：{digital_literacy}
每天可用时间：{time_commitment}

规则：
- 每个任务30分钟内能完成
- 第1-2天是"准备+发布"，不是"学习"
- 任务必须引用用户的具体经验（来自asset_map）
- 优先在选定平台操作
- 避免需要花钱的步骤
- 用大白话写任务描述，不要术语

输出JSON格式：
{{"tasks": [
  {{"day": 1, "task": "具体任务描述", "platform": "哪个平台", "estimated_time": "XX分钟", "why": "为什么今天做这个", "success_signal": "什么信号说明成功了"}},
  ...
]}}"""
```

Add this method to the `PromptBuilder` class:

```python
    def build_daily_tasks_prompt(
        self, platform: str, service_name: str, asset_map: str,
        market_signals: str, digital_literacy: str, time_commitment: str,
    ) -> str:
        return self.DAILY_TASKS_TEMPLATE.format(
            platform=platform, service_name=service_name,
            asset_map=asset_map, market_signals=market_signals,
            digital_literacy=digital_literacy, time_commitment=time_commitment,
        )
```

**Step 4: Run tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest -v`
Expected: All PASS

**Step 5: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add src/starting_point/llm/prompts.py tests/test_skills/test_other_skills.py
git commit -m "feat: add DAILY_TASKS_TEMPLATE prompt and builder method"
```

---

### Task 3: Rewrite CustomerAcquisitionSkill.generate_output

**Files:**
- Modify: `src/starting_point/skills/customer_acquisition.py`
- Test: `tests/test_skills/test_other_skills.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_other_skills.py`:

```python
@pytest.mark.asyncio
async def test_customer_acquisition_generates_daily_tasks():
    from unittest.mock import AsyncMock
    from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    llm.chat.return_value = '{"tasks": [{"day": 1, "task": "发帖子", "platform": "小红书", "estimated_time": "20分钟", "why": "原因", "success_signal": "有人问"}]}'

    skill = CustomerAcquisitionSkill(llm_client=llm)
    state = UserState(user_id="test")
    state.step_results.append(SkillStepResult(step_id="platform_choice", answer="xiaohongshu", selected_option="xiaohongshu"))
    state.step_results.append(SkillStepResult(step_id="content_readiness", answer="never"))
    state.step_results.append(SkillStepResult(step_id="confirm_plan", answer="ok"))

    output, updates = await skill.generate_output(state)
    assert "tasks" in output
    assert len(output["tasks"]) >= 1
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest tests/test_skills/test_other_skills.py::test_customer_acquisition_generates_daily_tasks -v`
Expected: FAIL (current output doesn't have "tasks" key)

**Step 3: Rewrite customer_acquisition.py**

Replace the entire `customer_acquisition.py` with:

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
    description = "7天逐日任务，每天一步，帮你接到第一个咨询"
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
            question="我帮你制定了7天行动计划。每天一个任务，30分钟内能完成。准备好了就开始吧！",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

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

        if self._llm is None:
            return {
                "skill_type": "customer_acquisition",
                "platform": platform_name,
                "tasks": [],
            }, {}

        prompt = self._prompt_builder.build_daily_tasks_prompt(
            platform=platform_name,
            service_name=service_name or "咨询服务",
            asset_map=asset_map_str or "用户行业经验",
            market_signals=market_signals_str or "暂无",
            digital_literacy=digital_literacy or "intermediate",
            time_commitment=time_commitment or "1-3h",
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
            }, {}

        return {
            "skill_type": "customer_acquisition",
            "platform": platform_name,
            "tasks": task_data.get("tasks", []),
        }, {}


def _parse_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": text}
```

**Step 4: Run tests**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run pytest -v`
Expected: All PASS

**Step 5: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add src/starting_point/skills/customer_acquisition.py tests/test_skills/test_other_skills.py
git commit -m "feat: rewrite CustomerAcquisitionSkill to generate 7-day daily task cards"
```

---

### Task 4: Rewrite frontend customer-acquisition.js

**Files:**
- Modify: `static/js/phases/customer-acquisition.js`

**Step 1: Rewrite the renderer**

Replace the entire `customer-acquisition.js` with:

```javascript
// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: 7-Day Daily Task Cards renderer

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

  const platform = data.platform || '小红书';
  const tasks = data.tasks || [];

  // Title card
  const titleCard = document.createElement('div');
  titleCard.className = 'output-card fade-in';
  titleCard.innerHTML = `
    <div class="output-card__title">7天行动计划</div>
    <div class="output-card__subtitle">平台: ${esc(platform)} · 每天30分钟内</div>
  `;
  wrapper.appendChild(titleCard);

  // Task cards
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
  const done = tasks.filter(t => isTaskCompleted(t.day)).length;
  return `7天行动计划 (${done}/${tasks.length} 完成)`;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
```

**Step 2: Add CSS for task cards**

Append to the existing CSS file (`static/design-system.css` or wherever styles live):

```css
/* Task Cards */
.task-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--sp-4);
  margin: var(--sp-3) 0;
  transition: opacity 0.3s ease;
}
.task-card--done {
  opacity: 0.6;
}
.task-card--done .task-card__task {
  text-decoration: line-through;
}
.task-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-2);
}
.task-card__checkbox {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  cursor: pointer;
}
.task-card__day {
  font-weight: 700;
  color: var(--text-primary);
}
.task-card__time {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
.task-card__task {
  font-size: var(--text-base);
  color: var(--text-primary);
  margin-bottom: var(--sp-2);
  line-height: 1.5;
}
.task-card__meta {
  margin-bottom: var(--sp-2);
}
.task-card__platform {
  display: inline-block;
  background: var(--surface-secondary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.task-card__why {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--sp-1);
}
.task-card__signal {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
```

**Step 3: Verify by running the dev server**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && uv run uvicorn starting_point.main:app --reload`

Navigate through the app to the "找到客户" phase and verify task cards render.

**Step 4: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add static/js/phases/customer-acquisition.js static/design-system.css
git commit -m "feat: rewrite customer-acquisition frontend with 7-day task card UI"
```

---

### Task 5: Fix self_discovery step count in index.js

**Files:**
- Modify: `static/js/phases/index.js`

**Step 1: Fix the hardcoded step count**

In `static/js/phases/index.js`, change line 6 from:

```javascript
  { id: 'self_discovery',       name: '发现金矿', steps: 8 },
```

to:

```javascript
  { id: 'self_discovery',       name: '发现金矿', steps: 11 },
```

**Step 2: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add static/js/phases/index.js
git commit -m "fix: update self_discovery step count from 8 to 11"
```

---

### Task 6: Full integration test

**Files:**
- Test: `tests/test_integration.py`

**Step 1: Update existing integration test**

The existing `test_full_self_discovery_with_market_signals` test should still pass. Verify it does.

**Step 2: Commit**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
git add tests/
git commit -m "test: verify all integration tests pass with Phase 2 changes"
```
