# Starting Point (启点) (启点) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Starting Point (启点) MVP — an AI-powered skill engine that guides unemployed mid-career professionals through self-discovery, offer creation, and first launch.

**Architecture:** Python/FastAPI backend with a skill engine pattern (inspired by gstack). Each skill is a self-contained Python module with a step-based workflow. DeepSeek API for Chinese-optimized text generation. SQLite for state persistence. Simple React frontend with chat + deliverables panels.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, httpx (DeepSeek), SQLite (aiosqlite), pytest, React 18, Next.js 14

---

## Project Structure

```
starting-point/
├── pyproject.toml
├── src/
│   └── starting_point/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app entry
│       ├── models.py               # All Pydantic data models
│       ├── config.py               # Settings (API keys, DB path)
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py           # DeepSeek API client
│       │   └── prompts.py          # Prompt templates
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── skill_base.py       # BaseSkill, Step, StepResult
│       │   ├── registry.py         # SkillRegistry
│       │   ├── runner.py           # SkillRunner (orchestrates steps)
│       │   └── state.py            # StateManager (SQLite)
│       ├── confidence/
│       │   ├── __init__.py
│       │   ├── engine.py           # ConfidenceEngine
│       │   └── patterns.py         # Negative emotion patterns
│       └── skills/
│           ├── __init__.py
│           ├── self_discovery.py   # Skill 1: /认识自己
│           ├── plan_path.py        # Skill 2: /规划路径
│           ├── take_action.py      # Skill 3: /开张行动
│           └── troubleshoot.py     # Skill 4: /卡住了
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_llm/
│   │   └── test_client.py
│   ├── test_engine/
│   │   ├── test_skill_base.py
│   │   ├── test_registry.py
│   │   ├── test_runner.py
│   │   └── test_state.py
│   ├── test_confidence/
│   │   └── test_engine.py
│   └── test_skills/
│       ├── test_self_discovery.py
│       ├── test_plan_path.py
│       ├── test_take_action.py
│       └── test_troubleshoot.py
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tsconfig.json
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   └── page.tsx
    │   ├── components/
    │   │   ├── ChatArea.tsx
    │   │   ├── DeliverablesPanel.tsx
    │   │   └── SkillProgress.tsx
    │   └── lib/
    │       └── api.ts
    └── tailwind.config.js
```

---

## Task 1: Project Scaffold & Dependencies

**Files:**
- Create: `starting-point/pyproject.toml`
- Create: `starting-point/src/starting_point/__init__.py`
- Create: `starting-point/src/starting_point/config.py`
- Create: `starting-point/tests/conftest.py`

**Step 1: Create project directory and pyproject.toml**

```bash
mkdir -p starting-point/src/starting_point
mkdir -p starting-point/tests
```

```toml
# starting-point/pyproject.toml
[project]
name = "starting-point"
version = "0.1.0"
description = "启点 — 帮助中年失业者将行业经验转化为收入"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.34.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.28.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/starting_point"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 2: Create config module**

```python
# starting-point/src/starting_point/config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    database_path: Path = Path("starting_point.db")
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_prefix": "CC_", "env_file": ".env"}


settings = Settings()
```

**Step 3: Create __init__.py**

```python
# starting-point/src/starting_point/__init__.py
"""Starting Point (启点) — 启点"""
```

**Step 4: Create test conftest**

```python
# starting-point/tests/conftest.py
import asyncio
import pytest


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Step 5: Create .env.example**

```
# starting-point/.env.example
CC_DEEPSEEK_API_KEY=your-api-key-here
CC_DATABASE_PATH=starting_point.db
```

**Step 6: Install dependencies and verify**

```bash
cd starting-point
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -c "from starting_point.config import settings; print('OK')"
```
Expected: `OK`

**Step 7: Commit**

```bash
cd ..
git add starting-point/
git commit -m "chore: scaffold starting-point project"
```

---

## Task 2: Data Models

**Files:**
- Create: `starting-point/src/starting_point/models.py`
- Create: `starting-point/tests/test_models.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_models.py
from starting_point.models import (
    StepOption, Step, SkillStepResult, SkillOutput,
    UserState, SkillType, ConfidenceLevel
)


def test_step_option_creation():
    option = StepOption(label="建材/装修", value="construction")
    assert option.label == "建材/装修"
    assert option.value == "construction"


def test_step_has_options_and_free_text():
    step = Step(
        id="industry",
        question="你在哪个行业干了多少年？",
        options=[
            StepOption(label="建材/装修", value="construction"),
            StepOption(label="餐饮/食品", value="food"),
        ],
        allow_free_text=True,
    )
    assert step.id == "industry"
    assert len(step.options) == 2
    assert step.allow_free_text is True


def test_skill_step_result_stores_answer():
    result = SkillStepResult(
        step_id="industry",
        answer="建材行业12年",
        selected_option=None,
        free_text="建材行业12年",
    )
    assert result.step_id == "industry"
    assert result.free_text == "建材行业12年"


def test_user_state_tracks_current_skill():
    state = UserState(user_id="test-user")
    assert state.current_skill == SkillType.SELF_DISCOVERY
    assert state.completed_steps == []


def test_confidence_level_values():
    assert ConfidenceLevel.LOW == "low"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.HIGH == "high"
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'starting_point.models'`

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/models.py
from __future__ import annotations

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class SkillType(str, Enum):
    SELF_DISCOVERY = "self_discovery"
    PLAN_PATH = "plan_path"
    TAKE_ACTION = "take_action"
    TROUBLESHOOT = "troubleshoot"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StepOption(BaseModel):
    label: str
    value: str


class Step(BaseModel):
    id: str
    question: str
    options: list[StepOption] = Field(default_factory=list)
    allow_free_text: bool = True
    confidence_boost_template: str | None = None


class SkillStepResult(BaseModel):
    step_id: str
    answer: str
    selected_option: str | None = None
    free_text: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class CapabilityItem(BaseModel):
    name: str
    description: str
    evidence: str
    estimated_value: str | None = None


class AssetMap(BaseModel):
    capabilities: list[CapabilityItem] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    raw_stories: list[str] = Field(default_factory=list)


class OfferItem(BaseModel):
    name: str
    target_customer: str
    pricing: str
    delivery_format: str
    why_fits: str
    first_step_7days: str
    backup_if_no_response: str | None = None


class LaunchContent(BaseModel):
    platform: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    publish_tips: list[str] = Field(default_factory=list)


class SkillOutput(BaseModel):
    skill_type: SkillType
    data: dict
    summary: str


class UserState(BaseModel):
    user_id: str
    current_skill: SkillType = SkillType.SELF_DISCOVERY
    current_step_index: int = 0
    completed_steps: list[str] = Field(default_factory=list)
    step_results: list[SkillStepResult] = Field(default_factory=list)
    asset_map: AssetMap | None = None
    selected_offer: OfferItem | None = None
    launched: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    options: list[StepOption] | None = None
    allow_free_text: bool = True
    step_id: str | None = None
    confidence_boost: str | None = None


class ChatRequest(BaseModel):
    user_id: str
    message: str
    selected_option: str | None = None


class ChatResponse(BaseModel):
    message: ChatMessage
    progress: float  # 0.0 to 1.0
    deliverable: SkillOutput | None = None
    skill_completed: bool = False
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_models.py -v
```
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/models.py starting-point/tests/test_models.py
git commit -m "feat: add Starting Point (启点) data models"
```

---

## Task 3: DeepSeek LLM Client

**Files:**
- Create: `starting-point/src/starting_point/llm/__init__.py`
- Create: `starting-point/src/starting_point/llm/client.py`
- Create: `starting-point/src/starting_point/llm/prompts.py`
- Create: `starting-point/tests/test_llm/test_client.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_llm/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder


@pytest.mark.asyncio
async def test_client_sends_chat_request():
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "你好！欢迎来到启点。"}}]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = lambda: None

    with patch("starting_point.llm.client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = DeepSeekClient(api_key="test-key")
        result = await client.chat(messages=[{"role": "user", "content": "你好"}])
        assert "你好" in result


def test_prompt_builder_system_prompt():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt(
        skill_name="认识自己",
        step_question="你在哪个行业干了多少年？",
        step_index=0,
        total_steps=8,
    )
    assert "认识自己" in prompt
    assert "启点" in prompt


def test_prompt_builder_confidence_boost():
    builder = PromptBuilder()
    boost = builder.build_confidence_boost(
        user_answer="我在建材行业干了12年",
        evidence_type="capability",
    )
    assert "建材" in boost
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_llm/test_client.py -v
```
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/llm/__init__.py
"""LLM client for DeepSeek API."""
```

```python
# starting-point/src/starting_point/llm/client.py
from __future__ import annotations

import httpx
from starting_point.config import settings


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url
        self._model = model or settings.deepseek_model

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
```

```python
# starting-point/src/starting_point/llm/prompts.py
from __future__ import annotations

SYSTEM_TEMPLATE = """你是"启点"的AI助手。你的任务是帮助中年失业者发现自己的行业经验价值，并帮助他们将这些经验转化为收入。

当前环节：{skill_name}（第{step_index}/{total_steps}步）
当前问题：{step_question}

核心原则：
1. 用接地气的语言，避免"赋能""生态""闭环"等术语
2. 每次只问一个问题
3. 有证据才鼓励，不把普通经历硬包装成稀缺能力
4. 如果用户回答太简短，用引导式追问
5. 检测到负面情绪时，先共情再给具体证据
"""

CONFIDENCE_BOOST_TEMPLATE = """基于用户刚才的回答："{user_answer}"

请生成一段简短、具体的正向反馈（2-3句话）。
要求：
- 引用用户原话中的具体内容
- 把经验翻译成"值多少钱"或"能帮谁"
- 不要空泛的表扬
- 证据类型：{evidence_type}
"""

EXTRACTION_TEMPLATE = """从以下对话中提取用户的可变现资产。

用户回答：
{answers}

请提取：
1. 可变现的知识点（具体的，不是泛泛的"有经验"）
2. 可用资源（渠道、人脉、报价信息等）
3. 信心评估（基于回答的具体程度和积极性）

输出为JSON格式：
{{"capabilities": [{{"name": "...", "description": "...", "evidence": "...", "estimated_value": "..."}}], "resources": ["..."], "confidence_level": "low|medium|high"}}
"""

OFFER_GENERATION_TEMPLATE = """基于用户的资产清单和约束条件，生成变现方案。

资产清单：{asset_map}
约束条件：{constraints}

请生成3个具体的offer方案，每个包含：
- 服务名称
- 目标客户
- 定价建议
- 交付形式
- 为什么适合这个人
- 7天内第一步
- 如果没人回应的备选方案

输出为JSON数组。
"""

CONTENT_GENERATION_TEMPLATE = """基于以下offer，为{platform}生成一篇发布文案。

Offer信息：{offer}
用户行业背景：{background}

要求：
- 用真人口吻，不像AI广告
- 标题从买家痛点出发
- 包含具体的价格对比或省钱案例
- 包含标签/关键词
- 首次免费/低价吸引

输出JSON：{{"title": "...", "body": "...", "tags": [...], "publish_tips": [...]}}
"""


class PromptBuilder:
    def build_system_prompt(
        self,
        skill_name: str,
        step_question: str,
        step_index: int,
        total_steps: int,
    ) -> str:
        return SYSTEM_TEMPLATE.format(
            skill_name=skill_name,
            step_question=step_question,
            step_index=step_index + 1,
            total_steps=total_steps,
        )

    def build_confidence_boost(
        self,
        user_answer: str,
        evidence_type: str,
    ) -> str:
        return CONFIDENCE_BOOST_TEMPLATE.format(
            user_answer=user_answer,
            evidence_type=evidence_type,
        )

    def build_extraction_prompt(self, answers: str) -> str:
        return EXTRACTION_TEMPLATE.format(answers=answers)

    def build_offer_prompt(self, asset_map: str, constraints: str) -> str:
        return OFFER_GENERATION_TEMPLATE.format(
            asset_map=asset_map, constraints=constraints,
        )

    def build_content_prompt(
        self, platform: str, offer: str, background: str,
    ) -> str:
        return CONTENT_GENERATION_TEMPLATE.format(
            platform=platform, offer=offer, background=background,
        )
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_llm/ -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/llm/ starting-point/tests/test_llm/
git commit -m "feat: add DeepSeek LLM client and prompt templates"
```

---

## Task 4: Confidence Engine

**Files:**
- Create: `starting-point/src/starting_point/confidence/__init__.py`
- Create: `starting-point/src/starting_point/confidence/engine.py`
- Create: `starting-point/src/starting_point/confidence/patterns.py`
- Create: `starting-point/tests/test_confidence/test_engine.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_confidence/test_engine.py
from starting_point.confidence.engine import ConfidenceEngine
from starting_point.confidence.patterns import NEGATIVE_PATTERNS
from starting_point.models import ConfidenceLevel


def test_detect_negative_emotion():
    engine = ConfidenceEngine()
    assert engine.detect_negative_emotion("我不行，什么都不懂")
    assert engine.detect_negative_emotion("没什么用，都是过去的事了")
    assert not engine.detect_negative_emotion("我在建材行业干了12年")


def test_assess_confidence_from_answer():
    engine = ConfidenceEngine()
    short = engine.assess_from_answer("嗯，干了几年")
    detailed = engine.assess_from_answer(
        "我在建材行业干了12年，主要是瓷砖和地板。"
        "有一次客户要买80块一平的品牌砖，我帮他找到了35块的工程砖，"
        "质量一样，帮他省了4000多块。"
    )
    assert short == ConfidenceLevel.LOW
    assert detailed == ConfidenceLevel.HIGH


def test_should_boost_confidence():
    engine = ConfidenceEngine()
    assert not engine.should_boost_confidence("嗯嗯", has_evidence=False)
    assert engine.should_boost_confidence(
        "我帮客户省了3000块", has_evidence=True,
    )


def test_build_empathetic_response():
    engine = ConfidenceEngine()
    response = engine.build_empathetic_response(
        "我不行，什么都不懂",
        user_evidence=["在建材行业干了12年"],
    )
    assert "12年" in response
    assert "不是因为你不行" in response
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_confidence/ -v
```
Expected: FAIL

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/confidence/__init__.py
"""Confidence rebuilding engine."""
```

```python
# starting-point/src/starting_point/confidence/patterns.py
NEGATIVE_PATTERNS = [
    "我不行",
    "我做不到",
    "没什么用",
    "什么都不懂",
    "没什么经验",
    "不值钱",
    "比不上",
    "没人要",
    "没希望",
    "算了",
    "没意思",
    "老了",
    "过时了",
    "学不会",
    "不敢",
    "丢人",
    "不好意思",
    "白费",
    "浪费",
]
```

```python
# starting-point/src/starting_point/confidence/engine.py
from __future__ import annotations

from starting_point.confidence.patterns import NEGATIVE_PATTERNS
from starting_point.models import ConfidenceLevel


class ConfidenceEngine:
    def detect_negative_emotion(self, text: str) -> bool:
        return any(pattern in text for pattern in NEGATIVE_PATTERNS)

    def assess_from_answer(self, answer: str) -> ConfidenceLevel:
        if len(answer) < 10:
            return ConfidenceLevel.LOW
        has_specific_number = any(c.isdigit() for c in answer)
        has_detail = any(
            kw in answer
            for kw in ["帮", "省", "避", "解决", "客户", "项目", "经历"]
        )
        if has_specific_number and has_detail:
            return ConfidenceLevel.HIGH
        if has_detail or len(answer) > 50:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def should_boost_confidence(
        self, answer: str, has_evidence: bool,
    ) -> bool:
        if not has_evidence:
            return False
        if self.detect_negative_emotion(answer):
            return True
        return has_evidence

    def build_empathetic_response(
        self, negative_text: str, user_evidence: list[str],
    ) -> str:
        evidence_part = ""
        if user_evidence:
            evidence_part = f"你{user_evidence[0]}，"
        return (
            f"我理解你现在的感受。说实话，{evidence_part}"
            "被行业淘汰不是因为你不行，是因为整个行业在变。"
            "但你的经验和判断力没有变。"
        )
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_confidence/ -v
```
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/confidence/ starting-point/tests/test_confidence/
git commit -m "feat: add confidence rebuilding engine with negative emotion detection"
```

---

## Task 5: Skill Engine Core (Base Classes)

**Files:**
- Create: `starting-point/src/starting_point/engine/__init__.py`
- Create: `starting-point/src/starting_point/engine/skill_base.py`
- Create: `starting-point/tests/test_engine/test_skill_base.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_engine/test_skill_base.py
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, StepOption, SkillStepResult


class FakeSkill(BaseSkill):
    name = "测试Skill"
    description = "用于测试"
    order = 1

    steps = [
        Step(
            id="q1",
            question="问题1",
            options=[StepOption(label="A", value="a")],
        ),
        Step(
            id="q2",
            question="问题2",
            allow_free_text=True,
        ),
    ]

    def process_answer(self, step_id, answer, state):
        return StepResult(next_step=True)

    def generate_output(self, state):
        return {"result": "done"}


def test_skill_reports_progress():
    skill = FakeSkill()
    assert skill.total_steps == 2


def test_skill_gets_step_by_index():
    skill = FakeSkill()
    step = skill.get_step(0)
    assert step.id == "q1"
    assert step.question == "问题1"


def test_skill_is_complete():
    skill = FakeSkill()
    assert not skill.is_complete(step_index=0)
    assert skill.is_complete(step_index=2)


def test_step_result_default():
    result = StepResult(next_step=True)
    assert result.next_step is True
    assert result.confidence_boost is None
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_engine/test_skill_base.py -v
```

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/engine/__init__.py
"""Skill engine core components."""
```

```python
# starting-point/src/starting_point/engine/skill_base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

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
    def generate_output(self, state: UserState) -> dict:
        ...
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_engine/test_skill_base.py -v
```
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/engine/skill_base.py starting-point/tests/test_engine/test_skill_base.py starting-point/src/starting_point/engine/__init__.py
git commit -m "feat: add skill base class and step types"
```

---

## Task 6: Skill Registry

**Files:**
- Create: `starting-point/src/starting_point/engine/registry.py`
- Create: `starting-point/tests/test_engine/test_registry.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_engine/test_registry.py
from starting_point.engine.registry import SkillRegistry
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, SkillType, UserState


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
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_engine/test_registry.py -v
```

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/engine/registry.py
from __future__ import annotations

from starting_point.engine.skill_base import BaseSkill
from starting_point.models import SkillType


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
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_engine/test_registry.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/engine/registry.py starting-point/tests/test_engine/test_registry.py
git commit -m "feat: add skill registry"
```

---

## Task 7: State Manager (SQLite)

**Files:**
- Create: `starting-point/src/starting_point/engine/state.py`
- Create: `starting-point/tests/test_engine/test_state.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_engine/test_state.py
import pytest
import tempfile
from pathlib import Path
from starting_point.engine.state import StateManager
from starting_point.models import (
    UserState, SkillType, SkillStepResult, ConfidenceLevel,
)


@pytest.fixture
def state_manager(tmp_path):
    db_path = tmp_path / "test.db"
    manager = StateManager(db_path)
    return manager


@pytest.mark.asyncio
async def test_create_and_load_state(state_manager):
    await state_manager.initialize()
    state = UserState(user_id="user1")
    await state_manager.save_state(state)
    loaded = await state_manager.load_state("user1")
    assert loaded is not None
    assert loaded.user_id == "user1"
    assert loaded.current_skill == SkillType.SELF_DISCOVERY


@pytest.mark.asyncio
async def test_update_step_results(state_manager):
    await state_manager.initialize()
    state = UserState(user_id="user2")
    state.step_results.append(
        SkillStepResult(step_id="industry", answer="建材行业12年"),
    )
    state.current_step_index = 1
    await state_manager.save_state(state)
    loaded = await state_manager.load_state("user2")
    assert len(loaded.step_results) == 1
    assert loaded.step_results[0].answer == "建材行业12年"
    assert loaded.current_step_index == 1


@pytest.mark.asyncio
async def test_load_nonexistent_returns_none(state_manager):
    await state_manager.initialize()
    result = await state_manager.load_state("nobody")
    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_engine/test_state.py -v
```

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/engine/state.py
from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from starting_point.models import UserState


class StateManager:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            await db.commit()

    async def save_state(self, state: UserState) -> None:
        data = state.model_dump_json()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_states (user_id, data) VALUES (?, ?)",
                (state.user_id, data),
            )
            await db.commit()

    async def load_state(self, user_id: str) -> UserState | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM user_states WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return UserState.model_validate_json(row[0])
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_engine/test_state.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/engine/state.py starting-point/tests/test_engine/test_state.py
git commit -m "feat: add SQLite state manager"
```

---

## Task 8: Skill 1 — Self Discovery (/认识自己)

**Files:**
- Create: `starting-point/src/starting_point/skills/__init__.py`
- Create: `starting-point/src/starting_point/skills/self_discovery.py`
- Create: `starting-point/tests/test_skills/test_self_discovery.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_skills/test_self_discovery.py
from starting_point.skills.self_discovery import SelfDiscoverySkill
from starting_point.models import UserState


def test_skill_has_8_steps():
    skill = SelfDiscoverySkill()
    assert skill.total_steps == 8


def test_first_step_is_industry():
    skill = SelfDiscoverySkill()
    step = skill.get_step(0)
    assert step.id == "industry"
    assert len(step.options) > 0


def test_process_answer_returns_next_step():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    result = skill.process_answer("industry", "建材行业", state)
    assert result.next_step is True


def test_process_negative_answer_returns_boost():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    result = skill.process_answer("proud_moment", "我不行，没什么特别的", state)
    assert result.confidence_boost is not None


def test_generate_output_returns_asset_map():
    skill = SelfDiscoverySkill()
    state = UserState(user_id="test")
    state.step_results = [
        {"step_id": "industry", "answer": "建材行业12年"},
        {"step_id": "proud_moment", "answer": "帮客户省了3000块瓷砖钱"},
    ]
    output = skill.generate_output(state)
    assert "capabilities" in output or "result" in output
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_skills/test_self_discovery.py -v
```

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/skills/__init__.py
"""Starting Point (启点) skills."""
```

```python
# starting-point/src/starting_point/skills/self_discovery.py
from __future__ import annotations

from starting_point.confidence.engine import ConfidenceEngine
from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, StepOption, UserState


class SelfDiscoverySkill(BaseSkill):
    name = "认识自己"
    description = "引导用户梳理经验，发现可变现能力"
    order = 1

    steps = [
        Step(
            id="industry",
            question="你在哪个行业干了多少年？",
            options=[
                StepOption(label="建材/装修", value="construction"),
                StepOption(label="餐饮/食品", value="food"),
                StepOption(label="零售/电商", value="retail"),
                StepOption(label="制造业", value="manufacturing"),
                StepOption(label="物流/运输", value="logistics"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="proud_moment",
            question="过去10年，哪件事你做得比身边大多数同行都稳？",
            allow_free_text=True,
        ),
        Step(
            id="save_money_story",
            question="讲一个你帮别人省钱或避坑的真实例子，越具体越好。",
            allow_free_text=True,
            confidence_boost_template="evidence_replay",
        ),
        Step(
            id="insider_knowledge",
            question=(
                "你知道哪些"行内人觉得正常，"
                "外行根本不知道"的信息？"
            ),
            allow_free_text=True,
        ),
        Step(
            id="people_ask_me",
            question="以前客户或同事最常因为什么来找你？",
            allow_free_text=True,
        ),
        Step(
            id="price_judgment",
            question="你能判断什么东西"贵了、坑了、不值"？",
            allow_free_text=True,
        ),
        Step(
            id="unique_resources",
            question=(
                "你有没有一类资源是别人短时间拿不到的："
                "报价、渠道、工厂、流程、名单、经验？"
            ),
            allow_free_text=True,
        ),
        Step(
            id="first_100",
            question=(
                "如果明天让你只靠经验赚到第一笔100元，"
                "你最可能卖什么帮助？"
            ),
            allow_free_text=True,
        ),
    ]

    def __init__(self) -> None:
        self._confidence = ConfidenceEngine()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        confidence_level = self._confidence.assess_from_answer(answer)

        if self._confidence.detect_negative_emotion(answer):
            evidences = [
                r.free_text or r.answer
                for r in state.step_results
                if r.free_text
            ]
            boost = self._confidence.build_empathetic_response(
                answer, evidences,
            )
            return StepResult(next_step=True, confidence_boost=boost)

        if self._confidence.should_boost_confidence(
            answer, has_evidence=(confidence_level.value == "high"),
        ):
            return StepResult(
                next_step=True,
                confidence_boost=f"很好！你的回答很具体。",
            )

        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        answers = []
        for result in state.step_results:
            answers.append(
                f"- {result.step_id}: {result.free_text or result.answer}"
            )
        return {
            "skill_type": "self_discovery",
            "answers": answers,
            "total_steps_completed": len(state.step_results),
        }
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_skills/test_self_discovery.py -v
```
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/skills/ starting-point/tests/test_skills/
git commit -m "feat: implement Self Discovery skill with confidence engine"
```

---

## Task 9: Skills 2-4 (Plan Path, Take Action, Troubleshoot)

**Files:**
- Create: `starting-point/src/starting_point/skills/plan_path.py`
- Create: `starting-point/src/starting_point/skills/take_action.py`
- Create: `starting-point/src/starting_point/skills/troubleshoot.py`
- Create: `starting-point/tests/test_skills/test_plan_path.py`
- Create: `starting-point/tests/test_skills/test_take_action.py`
- Create: `starting-point/tests/test_skills/test_troubleshoot.py`

**Step 1: Write the tests**

```python
# starting-point/tests/test_skills/test_plan_path.py
from starting_point.skills.plan_path import PlanPathSkill
from starting_point.models import UserState


def test_skill_has_6_steps():
    skill = PlanPathSkill()
    assert skill.total_steps == 6


def test_first_step_is_urgency():
    skill = PlanPathSkill()
    step = skill.get_step(0)
    assert step.id == "urgency"
    assert len(step.options) >= 2


def test_process_answer_returns_next():
    skill = PlanPathSkill()
    state = UserState(user_id="test")
    result = skill.process_answer("urgency", "几天内见到钱", state)
    assert result.next_step is True
```

```python
# starting-point/tests/test_skills/test_take_action.py
from starting_point.skills.take_action import TakeActionSkill
from starting_point.models import UserState


def test_skill_has_2_steps():
    skill = TakeActionSkill()
    assert skill.total_steps == 2


def test_first_step_is_platform():
    skill = TakeActionSkill()
    step = skill.get_step(0)
    assert step.id == "platform"
```

```python
# starting-point/tests/test_skills/test_troubleshoot.py
from starting_point.skills.troubleshoot import TroubleshootSkill
from starting_point.models import UserState


def test_skill_has_1_step():
    skill = TroubleshootSkill()
    assert skill.total_steps == 1


def test_step_is_problem_type():
    skill = TroubleshootSkill()
    step = skill.get_step(0)
    assert step.id == "problem_type"
    assert len(step.options) == 4
```

**Step 2: Run tests to verify they fail**

```bash
cd starting-point && python -m pytest tests/test_skills/ -v
```

**Step 3: Write the implementations**

```python
# starting-point/src/starting_point/skills/plan_path.py
from __future__ import annotations

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, StepOption, UserState


class PlanPathSkill(BaseSkill):
    name = "规划路径"
    description = "基于能力地图，推荐变现方向并拆解步骤"
    order = 2

    steps = [
        Step(
            id="urgency",
            question="你现在最急的是几天内见到钱，还是先把口碑做起来？",
            options=[
                StepOption(label="几天内就要见到钱", value="fast"),
                StepOption(label="可以先做口碑", value="reputation"),
                StepOption(label="都可以，看哪个靠谱", value="flexible"),
            ],
        ),
        Step(
            id="comfort_with_people",
            question="你愿不愿意直接和陌生人聊天或打电话？",
            options=[
                StepOption(label="愿意，没问题", value="yes"),
                StepOption(label="可以，但不太自在", value="hesitant"),
                StepOption(label="不愿意，想通过文字", value="text_only"),
            ],
        ),
        Step(
            id="service_format",
            question="你更能接受卖什么？",
            options=[
                StepOption(label="卖服务（咨询/指导/代办）", value="service"),
                StepOption(label="卖信息（清单/报告/推荐）", value="info"),
                StepOption(label="撮合（帮买卖双方牵线）", value="matchmaking"),
            ],
        ),
        Step(
            id="time_budget",
            question="你每周能投入几小时？",
            options=[
                StepOption(label="2小时以内", value="minimal"),
                StepOption(label="2-5小时", value="moderate"),
                StepOption(label="5小时以上", value="committed"),
            ],
        ),
        Step(
            id="free_first",
            question="你能接受首次免费换一个好评吗？",
            options=[
                StepOption(label="可以，先建立信任", value="yes"),
                StepOption(label="不行，必须收费", value="no"),
            ],
        ),
        Step(
            id="wont_do",
            question="你最不愿意做的事情是什么？（说出来我们帮你避开）",
            allow_free_text=True,
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        answers = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }
        return {
            "skill_type": "plan_path",
            "constraints": answers,
        }
```

```python
# starting-point/src/starting_point/skills/take_action.py
from __future__ import annotations

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, StepOption, UserState


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
            allow_free_text=True,
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        return {"skill_type": "take_action", "status": "content_generated"}
```

```python
# starting-point/src/starting_point/skills/troubleshoot.py
from __future__ import annotations

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.models import Step, StepOption, UserState


class TroubleshootSkill(BaseSkill):
    name = "卡住了"
    description = "你卡在哪了？帮你解决问题"
    order = 4

    steps = [
        Step(
            id="problem_type",
            question="你遇到了什么问题？",
            options=[
                StepOption(
                    label="不知道怎么做",
                    value="dont_know_how",
                ),
                StepOption(
                    label="做了但效果不好",
                    value="not_working",
                ),
                StepOption(
                    label="有技术困难",
                    value="technical",
                ),
                StepOption(
                    label="有心理障碍",
                    value="psychological",
                ),
            ],
            allow_free_text=True,
        ),
    ]

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    def generate_output(self, state: UserState) -> dict:
        return {"skill_type": "troubleshoot", "status": "resolved"}
```

**Step 4: Run all skill tests**

```bash
cd starting-point && python -m pytest tests/test_skills/ -v
```
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/skills/ starting-point/tests/test_skills/
git commit -m "feat: implement Plan Path, Take Action, and Troubleshoot skills"
```

---

## Task 10: Skill Runner (Orchestrator)

**Files:**
- Create: `starting-point/src/starting_point/engine/runner.py`
- Create: `starting-point/tests/test_engine/test_runner.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_engine/test_runner.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from starting_point.engine.runner import SkillRunner
from starting_point.engine.registry import SkillRegistry
from starting_point.engine.state import StateManager
from starting_point.engine.skill_base import StepResult
from starting_point.models import (
    SkillType, UserState, Step, ChatMessage, ChatResponse,
)
from starting_point.skills.self_discovery import SelfDiscoverySkill
from pathlib import Path


@pytest.fixture
def runner(tmp_path):
    registry = SkillRegistry()
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill())
    state_mgr = StateManager(tmp_path / "test.db")
    return SkillRunner(registry, state_mgr, llm_client=None)


@pytest.mark.asyncio
async def test_start_conversation_returns_first_question(runner):
    await runner.state_manager.initialize()
    response = await runner.process_message("user1", "开始", None)
    assert response.message.role == "assistant"
    assert response.message.step_id == "industry"
    assert response.progress == 0.0


@pytest.mark.asyncio
async def test_answer_advances_to_next_step(runner):
    await runner.state_manager.initialize()
    await runner.process_message("user1", "开始", None)
    response = await runner.process_message(
        "user1", "建材行业12年", None,
    )
    assert response.message.step_id == "proud_moment"
    assert response.progress > 0.0


@pytest.mark.asyncio
async def test_go_back_to_previous_step(runner):
    await runner.state_manager.initialize()
    await runner.process_message("user1", "开始", None)
    await runner.process_message("user1", "建材", None)
    response = await runner.go_back("user1", target_step="industry")
    assert response.message.step_id == "industry"
```

**Step 2: Run test to verify it fails**

```bash
cd starting-point && python -m pytest tests/test_engine/test_runner.py -v
```

**Step 3: Write the implementation**

```python
# starting-point/src/starting_point/engine/runner.py
from __future__ import annotations

from starting_point.engine.registry import SkillRegistry
from starting_point.engine.state import StateManager
from starting_point.models import (
    ChatMessage, ChatResponse, SkillType, UserState, SkillOutput,
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

        if state.current_step_index == 0 and not state.step_results:
            step = skill.get_step(0)
            return self._build_step_response(step, 0, skill.total_steps)

        step = skill.get_step(state.current_step_index)
        if step is None:
            output_data = skill.generate_output(state)
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

        from starting_point.models import SkillStepResult

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
            output_data = skill.generate_output(state)
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
```

**Step 4: Run test to verify it passes**

```bash
cd starting-point && python -m pytest tests/test_engine/test_runner.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
cd .. && git add starting-point/src/starting_point/engine/runner.py starting-point/tests/test_engine/test_runner.py
git commit -m "feat: add skill runner orchestrator with back navigation"
```

---

## Task 11: FastAPI Application

**Files:**
- Create: `starting-point/src/starting_point/main.py`

**Step 1: Write the implementation**

```python
# starting-point/src/starting_point/main.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from starting_point.config import settings
from starting_point.engine.registry import SkillRegistry
from starting_point.engine.runner import SkillRunner
from starting_point.engine.state import StateManager
from starting_point.llm.client import DeepSeekClient
from starting_point.models import ChatRequest, ChatResponse, SkillType
from starting_point.skills.self_discovery import SelfDiscoverySkill
from starting_point.skills.plan_path import PlanPathSkill
from starting_point.skills.take_action import TakeActionSkill
from starting_point.skills.troubleshoot import TroubleshootSkill


def create_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill())
    registry.register(SkillType.PLAN_PATH, PlanPathSkill())
    registry.register(SkillType.TAKE_ACTION, TakeActionSkill())
    registry.register(SkillType.TROUBLESHOOT, TroubleshootSkill())
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = create_registry()
    state_manager = StateManager(settings.database_path)
    await state_manager.initialize()
    llm_client = DeepSeekClient() if settings.deepseek_api_key else None
    app.state.runner = SkillRunner(registry, state_manager, llm_client)
    yield


app = FastAPI(
    title="Starting Point (启点) API",
    description="启点",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    runner: SkillRunner = app.state.runner
    return await runner.process_message(
        request.user_id, request.message, request.selected_option,
    )


@app.post("/api/back/{user_id}/{step_id}", response_model=ChatResponse)
async def go_back(user_id: str, step_id: str) -> ChatResponse:
    runner: SkillRunner = app.state.runner
    return await runner.go_back(user_id, step_id)


@app.get("/api/state/{user_id}")
async def get_state(user_id: str):
    runner: SkillRunner = app.state.runner
    state = await runner.state_manager.load_state(user_id)
    if state is None:
        return {"error": "User not found"}
    return state.model_dump()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
```

**Step 2: Verify the app starts**

```bash
cd starting-point && python -c "from starting_point.main import app; print('App created:', app.title)"
```
Expected: `App created: Starting Point (启点) API`

**Step 3: Commit**

```bash
cd .. && git add starting-point/src/starting_point/main.py
git commit -m "feat: add FastAPI application with chat and state endpoints"
```

---

## Task 12: Frontend (React/Next.js)

**Files:**
- Create: `starting-point/frontend/` (full Next.js app)

**Step 1: Scaffold Next.js app**

```bash
cd starting-point
npx create-next-app@latest frontend --typescript --tailwind --app --no-eslint --no-src-dir --import-alias "@/*"
```

**Step 2: Create API client**

```typescript
// starting-point/frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface StepOption {
  label: string;
  value: string;
}

export interface ChatMessageData {
  role: "user" | "assistant" | "system";
  content: string;
  options: StepOption[] | null;
  allow_free_text: boolean;
  step_id: string | null;
  confidence_boost: string | null;
}

export interface ChatResponseData {
  message: ChatMessageData;
  progress: number;
  deliverable: any | null;
  skill_completed: boolean;
}

export async function sendMessage(
  userId: string,
  message: string,
  selectedOption: string | null,
): Promise<ChatResponseData> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      message,
      selected_option: selectedOption,
    }),
  });
  return res.json();
}

export async function goBack(
  userId: string,
  stepId: string,
): Promise<ChatResponseData> {
  const res = await fetch(`${API_BASE}/api/back/${userId}/${stepId}`, {
    method: "POST",
  });
  return res.json();
}
```

**Step 3: Create main page component**

```tsx
// starting-point/frontend/src/app/page.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { sendMessage, goBack, ChatResponseData, StepOption } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  options: StepOption[] | null;
  allowFreeText: boolean;
  stepId: string | null;
  confidenceBoost: string | null;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [progress, setProgress] = useState(0);
  const [userId] = useState(() => `user-${Date.now()}`);
  const [loading, setLoading] = useState(false);
  const [currentStepId, setCurrentStepId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    startConversation();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function startConversation() {
    setLoading(true);
    try {
      const data = await sendMessage(userId, "开始", null);
      handleResponse(data);
    } finally {
      setLoading(false);
    }
  }

  function handleResponse(data: ChatResponseData) {
    setProgress(data.progress);
    setCurrentStepId(data.message.step_id);
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: data.message.content,
        options: data.message.options,
        allowFreeText: data.message.allow_free_text,
        stepId: data.message.step_id,
        confidenceBoost: data.message.confidence_boost,
      },
    ]);
  }

  async function handleSend(text: string, option: string | null) {
    if (!text && !option) return;
    const displayText = option
      ? messages[messages.length - 1]?.options?.find(
          (o) => o.value === option,
        )?.label || option
      : text;

    setMessages((prev) => [
      ...prev,
      { role: "user" as const, content: displayText, options: null, allowFreeText: true, stepId: null, confidenceBoost: null },
    ]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendMessage(userId, text || option || "", option);
      handleResponse(data);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoBack() {
    if (messages.length < 2) return;
    const stepId = currentStepId;
    if (!stepId) return;

    setLoading(true);
    try {
      const data = await goBack(userId, stepId);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: data.message.content,
          options: data.message.options,
          allowFreeText: data.message.allow_free_text,
          stepId: data.message.step_id,
          confidenceBoost: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const lastMessage = messages[messages.length - 1];
  const showOptions = lastMessage?.role === "assistant" && lastMessage.options?.length;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between">
        <h1 className="text-lg font-bold text-gray-900">启点</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            {Math.round(progress * 100)}%
          </span>
          <div className="w-32 h-2 bg-gray-200 rounded-full">
            <div
              className="h-2 bg-blue-500 rounded-full transition-all"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-4 max-w-2xl mx-auto w-full">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-blue-500 text-white"
                  : "bg-white shadow text-gray-900"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.confidenceBoost && (
                <p className="mt-2 text-sm text-green-600 italic">
                  {msg.confidenceBoost}
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white shadow rounded-2xl px-4 py-3">
              <span className="animate-pulse">正在思考...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t px-4 py-3">
        {showOptions && (
          <div className="flex flex-wrap gap-2 mb-3">
            {lastMessage.options!.map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleSend("", opt.value)}
                disabled={loading}
                className="px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm hover:bg-blue-100 disabled:opacity-50"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleGoBack}
            disabled={messages.length < 2 || loading}
            className="px-3 py-2 text-gray-500 hover:text-gray-700 disabled:opacity-30"
          >
            ← 回退
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && handleSend(input, null)
            }
            placeholder="输入你的回答..."
            disabled={loading}
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend(input, null)}
            disabled={loading || !input}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </footer>
    </div>
  );
}
```

**Step 4: Verify frontend builds**

```bash
cd starting-point/frontend && npm run build
```
Expected: Build succeeds

**Step 5: Commit**

```bash
cd ../.. && git add starting-point/frontend/
git commit -m "feat: add React/Next.js frontend with chat interface"
```

---

## Task 13: Integration Test

**Files:**
- Create: `starting-point/tests/test_integration.py`

**Step 1: Write the test**

```python
# starting-point/tests/test_integration.py
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from starting_point.main import app, create_registry
from starting_point.engine.state import StateManager
from starting_point.engine.runner import SkillRunner
from starting_point.models import ChatRequest


@pytest.fixture
async def client(tmp_path):
    registry = create_registry()
    state_mgr = StateManager(tmp_path / "test.db")
    await state_mgr.initialize()
    app.state.runner = SkillRunner(registry, state_mgr, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_full_chat_flow(client):
    # Start conversation
    resp = await client.post("/api/chat", json={
        "user_id": "int-test",
        "message": "开始",
        "selected_option": None,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["step_id"] == "industry"

    # Answer industry
    resp = await client.post("/api/chat", json={
        "user_id": "int-test",
        "message": "建材行业12年",
        "selected_option": None,
    })
    data = resp.json()
    assert data["message"]["step_id"] == "proud_moment"

    # Go back
    resp = await client.post("/api/back/int-test/industry")
    data = resp.json()
    assert data["message"]["step_id"] == "industry"
```

**Step 2: Run the integration test**

```bash
cd starting-point && python -m pytest tests/test_integration.py -v
```
Expected: PASS

**Step 3: Commit**

```bash
cd .. && git add starting-point/tests/test_integration.py
git commit -m "test: add integration test for full chat flow"
```

---

## Task 14: Run All Tests & Final Verification

**Step 1: Run the full test suite**

```bash
cd starting-point && python -m pytest tests/ -v --tb=short
```
Expected: All tests PASS

**Step 2: Start the backend**

```bash
cd starting-point && DEEPSEEK_API_KEY=your-key python -m starting_point.main
```

**Step 3: Start the frontend (separate terminal)**

```bash
cd starting-point/frontend && npm run dev
```

**Step 4: Verify at http://localhost:3000**

- Chat interface loads
- First question appears
- Can type answer and submit
- Next question appears
- Back button works

**Step 5: Final commit**

```bash
cd .. && git add -A && git commit -m "chore: final verification, all tests passing"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Project scaffold & deps | 15 min |
| 2 | Data models | 20 min |
| 3 | DeepSeek LLM client | 25 min |
| 4 | Confidence engine | 20 min |
| 5 | Skill engine base classes | 20 min |
| 6 | Skill registry | 15 min |
| 7 | State manager (SQLite) | 20 min |
| 8 | Skill 1: Self Discovery | 30 min |
| 9 | Skills 2-4 | 30 min |
| 10 | Skill runner | 30 min |
| 11 | FastAPI application | 20 min |
| 12 | React frontend | 45 min |
| 13 | Integration test | 15 min |
| 14 | Final verification | 15 min |
| **Total** | | **~5 hours** |

**Build order dependency:**
```
Task 1 → Task 2 → Task 3 (LLM) + Task 4 (Confidence) [parallel]
                  → Task 5 (Base) → Task 6 (Registry) + Task 7 (State) [parallel]
                  → Task 8 (Skill 1) → Task 9 (Skills 2-4)
                  → Task 10 (Runner) → Task 11 (API) + Task 12 (Frontend) [parallel]
                  → Task 13 (Integration) → Task 14 (Verify)
```
