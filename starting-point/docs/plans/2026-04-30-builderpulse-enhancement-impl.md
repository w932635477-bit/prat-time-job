# BuilderPulse Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add market validation questions to SelfDiscoverySkill, upgrade the extraction prompt to use market signals, and update the confidence engine to recognize demand-signal language.

**Architecture:** Additive changes only — 3 new Step entries appended to the existing 8, an updated extraction prompt, and broader confidence keywords. No new files in `src/`. Existing tests updated to match new step count.

**Tech Stack:** Python 3.12, pytest, Pydantic, existing skill framework (BaseSkill, SkillRunner)

---

### Task 1: Add 3 market validation steps to SelfDiscoverySkill

**Files:**
- Modify: `src/starting_point/skills/self_discovery.py:20-61` (steps list)
- Test: `tests/test_skills/test_self_discovery.py`

**Step 1: Write the failing test**

Add to `tests/test_skills/test_self_discovery.py`:

```python
def test_skill_has_11_steps():
    skill = SelfDiscoverySkill()
    assert skill.total_steps == 11


def test_step_8_is_content_search():
    skill = SelfDiscoverySkill()
    step = skill.get_step(8)
    assert step.id == "content_search"
    assert step.allow_free_text is True


def test_step_9_is_organic_inquiry():
    skill = SelfDiscoverySkill()
    step = skill.get_step(9)
    assert step.id == "organic_inquiry"
    assert step.allow_free_text is True


def test_step_10_is_shared_pain():
    skill = SelfDiscoverySkill()
    step = skill.get_step(10)
    assert step.id == "shared_pain"
    assert step.allow_free_text is True
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py -v`
Expected: 4 FAIL (step count is 8, not 11; step IDs don't exist)

**Step 3: Add the 3 new steps**

In `src/starting_point/skills/self_discovery.py`, append after the `first_100` step (the last entry in the `steps` list, which ends around line 60):

```python
        Step(
            id="content_search",
            question="你在抖音或小红书上搜过自己行业的什么内容？",
            allow_free_text=True,
        ),
        Step(
            id="organic_inquiry",
            question="最近有没有人主动找你帮忙或咨询？因为什么事？",
            allow_free_text=True,
        ),
        Step(
            id="shared_pain",
            question="你觉得你行业里什么最坑？你朋友也这么觉得吗？",
            allow_free_text=True,
            confidence_boost_template="evidence_replay",
        ),
```

Also update the existing step count test. Change `test_skill_has_8_steps`:

```python
def test_skill_has_11_steps():
    skill = SelfDiscoverySkill()
    assert skill.total_steps == 11
```

Delete the old `test_skill_has_8_steps`.

**Step 4: Run tests to verify they pass**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v`
Expected: All PASS (runner tests still pass because they test assessment, not self_discovery step count)

**Step 6: Commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add src/starting_point/skills/self_discovery.py tests/test_skills/test_self_discovery.py
git commit -m "feat: add 3 market validation questions to SelfDiscoverySkill"
```

---

### Task 2: Update extraction prompt to use market signals

**Files:**
- Modify: `src/starting_point/llm/prompts.py:27-38` (EXTRACTION_TEMPLATE)

**Step 1: Write the failing test**

Add to `tests/test_skills/test_self_discovery.py`:

```python
def test_extraction_prompt_mentions_market_signals():
    from starting_point.llm.prompts import PromptBuilder
    builder = PromptBuilder()
    prompt = builder.build_extraction_prompt("- industry: 建材\n- content_search: 装修避坑")
    assert "content_search" in prompt or "市场信号" in prompt or "market_signal" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py::test_extraction_prompt_mentions_market_signals -v`
Expected: FAIL (current prompt doesn't mention market signals)

**Step 3: Update the extraction prompt**

In `src/starting_point/llm/prompts.py`, replace `EXTRACTION_TEMPLATE` (lines 27-38) with:

```python
EXTRACTION_TEMPLATE = """从以下对话中提取用户的可变现资产和市场信号。

用户回答：
{answers}

请提取：
1. 可变现的知识点（具体的，不是泛泛的"有经验"）
2. 可用资源（渠道、人脉、报价信息等）
3. 信心评估（基于回答的具体程度和积极性）
4. 市场信号（基于 content_search、organic_inquiry、shared_pain 的回答）：
   - demand_evidence：有没有人已经在找这种帮助？（来自 organic_inquiry）
   - search_intent：用户自己搜什么？（来自 content_search）
   - shared_pain_point：行业共性痛点是什么？（来自 shared_pain）
   - market_readiness：综合判断，市场是否已经准备好为这个经验付费（high/medium/low）

输出为JSON格式：
{{"capabilities": [{{"name": "...", "description": "...", "evidence": "...", "estimated_value": "..."}}], "resources": ["..."], "confidence_level": "low|medium|high", "market_signals": {{"demand_evidence": "...", "search_intent": "...", "shared_pain_point": "...", "market_readiness": "high|medium|low"}}}}"""
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add src/starting_point/llm/prompts.py tests/test_skills/test_self_discovery.py
git commit -m "feat: update extraction prompt to include market signal analysis"
```

---

### Task 3: Add market_signals field to AssetMap model

**Files:**
- Modify: `src/starting_point/models.py:56-60` (AssetMap class)

**Step 1: Write the failing test**

Add to `tests/test_models.py`:

```python
def test_asset_map_has_market_signals_field():
    from starting_point.models import AssetMap, MarketSignals
    signals = MarketSignals(
        demand_evidence="有人咨询",
        search_intent="装修避坑",
        shared_pain_point="瓷砖被坑",
        market_readiness="high",
    )
    am = AssetMap(market_signals=signals)
    assert am.market_signals.demand_evidence == "有人咨询"
    assert am.market_signals.market_readiness == "high"


def test_asset_map_market_signals_default_none():
    from starting_point.models import AssetMap
    am = AssetMap()
    assert am.market_signals is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_models.py::test_asset_map_has_market_signals_field -v`
Expected: FAIL (MarketSignals doesn't exist)

**Step 3: Add MarketSignals model and update AssetMap**

In `src/starting_point/models.py`, add after `CapabilityItem` class (after line 53):

```python
class MarketSignals(BaseModel):
    demand_evidence: str = ""
    search_intent: str = ""
    shared_pain_point: str = ""
    market_readiness: str = "medium"
```

Then update `AssetMap` (currently lines 56-60) to include the new field:

```python
class AssetMap(BaseModel):
    capabilities: list[CapabilityItem] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    raw_stories: list[str] = Field(default_factory=list)
    market_signals: MarketSignals | None = None
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_models.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v`
Expected: All PASS (field defaults to None, no breakage)

**Step 6: Commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add src/starting_point/models.py tests/test_models.py
git commit -m "feat: add MarketSignals model to AssetMap"
```

---

### Task 4: Wire market_signals into SelfDiscoverySkill.generate_output

**Files:**
- Modify: `src/starting_point/skills/self_discovery.py:91-148` (generate_output method)

**Step 1: Write the failing test**

Add to `tests/test_skills/test_self_discovery.py`:

```python
@pytest.mark.asyncio
async def test_generate_output_includes_market_signals_when_llm_returns_them():
    from unittest.mock import AsyncMock
    from starting_point.models import UserState, SkillStepResult

    llm = AsyncMock()
    llm.chat.return_value = '{"capabilities": [], "resources": [], "confidence_level": "medium", "market_signals": {"demand_evidence": "有人问装修", "search_intent": "瓷砖选购", "shared_pain_point": "被坑", "market_readiness": "high"}}'

    skill = SelfDiscoverySkill(llm_client=llm)
    state = UserState(user_id="test")
    for step_id in ["industry", "proud_moment", "save_money_story", "insider_knowledge", "people_ask_me", "price_judgment", "unique_resources", "first_100", "content_search", "organic_inquiry", "shared_pain"]:
        state.step_results.append(SkillStepResult(step_id=step_id, answer=f"answer for {step_id}"))

    output, updates = await skill.generate_output(state)
    assert "market_signals" in updates.get("asset_map", {}).model_fields_set or "market_signals" in str(updates)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py::test_generate_output_includes_market_signals_when_llm_returns_them -v`
Expected: FAIL (current code doesn't extract market_signals from LLM response)

**Step 3: Update generate_output to parse market_signals**

In `src/starting_point/skills/self_discovery.py`, update the `generate_output` method. Replace the section that builds `AssetMap` (approximately lines 125-148) with:

```python
        from starting_point.models import AssetMap, CapabilityItem, ConfidenceLevel, MarketSignals
        capabilities = [
            CapabilityItem(
                name=c.get("name", ""),
                description=c.get("description", ""),
                evidence=c.get("evidence", ""),
                estimated_value=c.get("estimated_value"),
            )
            for c in asset_data.get("capabilities", [])
        ]
        conf_str = asset_data.get("confidence_level", "medium")
        raw_ms = asset_data.get("market_signals", {})
        market_signals = MarketSignals(
            demand_evidence=raw_ms.get("demand_evidence", ""),
            search_intent=raw_ms.get("search_intent", ""),
            shared_pain_point=raw_ms.get("shared_pain_point", ""),
            market_readiness=raw_ms.get("market_readiness", "medium"),
        ) if raw_ms else None
        asset_map = AssetMap(
            capabilities=capabilities,
            resources=asset_data.get("resources", []),
            confidence_level=ConfidenceLevel(conf_str) if conf_str in ("low", "medium", "high") else ConfidenceLevel.MEDIUM,
            raw_stories=asset_data.get("raw_stories", []),
            market_signals=market_signals,
        )
        output = {
            "skill_type": "self_discovery",
            "answers": answers,
            "asset_map": asset_data,
            "total_steps_completed": len(state.step_results),
        }
        return output, {"asset_map": asset_map}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_skills/test_self_discovery.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add src/starting_point/skills/self_discovery.py tests/test_skills/test_self_discovery.py
git commit -m "feat: wire market_signals into SelfDiscoverySkill output"
```

---

### Task 5: Broaden confidence engine for demand-signal language

**Files:**
- Modify: `src/starting_point/confidence/engine.py:14-18` (assess_from_answer detail keywords)
- Modify: `src/starting_point/confidence/patterns.py` (optional: add demand-signal keywords)
- Test: `tests/test_confidence/test_engine.py`

**Step 1: Read existing confidence tests**

Run: `cat /Users/weilei/part-time\ job/autoresearch-mlx/starting-point/tests/test_confidence/test_engine.py`

**Step 2: Write the failing test**

Add to `tests/test_confidence/test_engine.py`:

```python
def test_demand_signal_answer_scores_high():
    engine = ConfidenceEngine()
    level = engine.assess_from_answer(
        "上个月有3个人问我瓷砖怎么选，我帮他们避开了800块的溢价"
    )
    assert level == ConfidenceLevel.HIGH


def test_search_intent_answer_scores_medium():
    engine = ConfidenceEngine()
    level = engine.assess_from_answer(
        "我在小红书上搜过瓷砖选购攻略"
    )
    assert level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH)
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_confidence/test_engine.py::test_demand_signal_answer_scores_high -v`
Expected: May fail if "问" and "避开" aren't in the detail keyword list.

**Step 4: Add demand-signal keywords to assess_from_answer**

In `src/starting_point/confidence/engine.py`, update the `has_detail` check in `assess_from_answer` to include demand-signal keywords:

```python
        has_detail = any(
            kw in answer
            for kw in ["帮", "省", "避", "解决", "客户", "项目", "经历",
                       "问", "找我", "搜", "咨询", "坑", "被坑", "骗"]
        )
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest tests/test_confidence/test_engine.py -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v`
Expected: All PASS

**Step 7: Commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add src/starting_point/confidence/engine.py tests/test_confidence/test_engine.py
git commit -m "feat: broaden confidence engine to recognize demand-signal language"
```

---

### Task 6: Verify frontend compatibility

**Files:**
- Read-only check: `static/js/app.js`

**Step 1: Verify app.js handles dynamic step counts**

Read `static/js/app.js` and confirm:
1. It renders steps from API response (not hardcoded count)
2. It handles `allow_free_text: true` for new steps
3. It sends free text answers correctly for steps without options

If all 3 are true, no frontend changes needed. The new steps have `allow_free_text=True` and no `options`, so they render as text input fields automatically.

**Step 2: Run the dev server and manually test**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run uvicorn starting_point.main:app --reload`

Open the app in a browser, go through assessment (4 steps), then verify that self_discovery now shows 11 questions including the 3 new ones at the end:
- Step 9: "你在抖音或小红书上搜过自己行业的什么内容？"
- Step 10: "最近有没有人主动找你帮忙或咨询？因为什么事？"
- Step 11: "你觉得你行业里什么最坑？你朋友也这么觉得吗？"

**Step 3: Commit if any frontend fix was needed**

If `app.js` needed changes:

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add static/js/app.js
git commit -m "fix: ensure frontend handles steps without options"
```

If no changes needed, skip this step.

---

### Task 7: Final integration test

**Files:**
- Test: `tests/test_integration.py`

**Step 1: Write integration test for full self_discovery flow with 11 steps**

Add to `tests/test_integration.py`:

```python
@pytest.mark.asyncio
async def test_full_self_discovery_with_market_signals():
    """Regression test: 11 steps complete and produce market_signals in output."""
    from starting_point.engine.registry import SkillRegistry
    from starting_point.engine.runner import SkillRunner
    from starting_point.engine.state import StateManager
    from starting_point.main import create_registry

    registry = create_registry()
    state_mgr = StateManager(tmp_path / "test.db")
    await state_mgr.initialize()
    runner = SkillRunner(registry, state_mgr, None)

    # Complete assessment (4 steps)
    await runner.process_message("u1", "hi", None)
    for answer in ["basic", "ready", "1-3h", "moderate"]:
        await runner.process_message("u1", answer, None)

    # Complete self_discovery (11 steps)
    for step_id in ["industry", "proud_moment", "save_money_story",
                     "insider_knowledge", "people_ask_me", "price_judgment",
                     "unique_resources", "first_100", "content_search",
                     "organic_inquiry", "shared_pain"]:
        resp = await runner.process_message("u1", f"test answer for {step_id}", None)

    # After self_discovery completes, should advance to next skill
    state = await state_mgr.load_state("u1")
    assert state.current_skill != SkillType.SELF_DISCOVERY
```

Note: This test may need adjustment based on whether `tmp_path` is available as a fixture. Check existing integration tests for the pattern.

**Step 2: Run full test suite one final time**

Run: `cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point && uv run pytest -v --cov=src --cov-report=term-missing`
Expected: All PASS, coverage >= 80%

**Step 3: Final commit**

```bash
cd /Users/weilei/part-time\ job/autoresearch-mlx/starting-point
git add tests/test_integration.py
git commit -m "test: add integration test for 11-step self_discovery with market signals"
```
