# Starting Point V2 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将启点从"帮你认识自己"变成"陪你赚到第一块钱"，实现6阶段全流程引导。

**Architecture:** 在现有 FastAPI + SkillRegistry + SkillRunner + StateManager 架构上扩展。新增5个Skill（Assessment, ProductPackaging, CustomerAcquisition, FirstDeal, Growth），增强SelfDiscovery。扩展UserState支持多阶段数据和30天内容计划。

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, aiosqlite, httpx (DeepSeek client), pytest

**Design Doc:** `docs/plans/2026-04-27-starting-point-v2-full-flow-design.md`

---

## Task 1: 扩展数据模型

**Files:**
- Modify: `src/starting_point/models.py`

**Step 1: 写失败测试**

```python
# tests/test_models.py 末尾追加

def test_skill_type_has_v2_phases():
    """V2 新增5个阶段对应的 SkillType。"""
    assert hasattr(SkillType, "ASSESSMENT")
    assert hasattr(SkillType, "PRODUCT_PACKAGING")
    assert hasattr(SkillType, "CUSTOMER_ACQUISITION")
    assert hasattr(SkillType, "FIRST_DEAL")
    assert hasattr(SkillType, "GROWTH")


def test_user_assessment_model():
    """阶段0评估产出模型。"""
    a = UserAssessment(
        digital_literacy="basic",
        mental_readiness="exploring",
        time_commitment="1-3h",
        financial_pressure="moderate",
        profile_tag="有基础+愿意试+时间一般+低压力",
        content_pace="normal",
        first_milestone="获得第一个咨询",
        expectation_tone="中速，每天1条",
    )
    assert a.digital_literacy == "basic"


def test_content_plan_model():
    """30天内容计划模型。"""
    plan = ContentPlan(
        platform="xiaohongshu",
        total_pieces=30,
        weeks=[
            ContentWeek(week=1, theme="试水期", pieces=7, status="not_started"),
            ContentWeek(week=2, theme="找感觉期", pieces=7, status="not_started"),
            ContentWeek(week=3, theme="突破期", pieces=8, status="not_started"),
            ContentWeek(week=4, theme="收获期", pieces=8, status="not_started"),
        ],
    )
    assert plan.total_pieces == 30
    assert len(plan.weeks) == 4


def test_phase_result_model():
    """各阶段产出存储模型。"""
    pr = PhaseResult(
        phase=0,
        data={"profile_tag": "test"},
        version=1,
    )
    assert pr.phase == 0


def test_user_state_has_v2_fields():
    """UserState 支持 V2 多阶段字段。"""
    state = UserState(user_id="v2test")
    assert hasattr(state, "assessment")
    assert hasattr(state, "phase_results")
    assert hasattr(state, "content_plan")
    assert state.phase_results == {}
```

**Step 2: 运行测试确认失败**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_models.py::test_skill_type_has_v2_phases -v`
Expected: FAIL — `ASSESSMENT` not in SkillType

**Step 3: 实现模型变更**

在 `models.py` 中：

1. 扩展 `SkillType` 枚举：
```python
class SkillType(str, Enum):
    ASSESSMENT = "assessment"
    SELF_DISCOVERY = "self_discovery"
    PRODUCT_PACKAGING = "product_packaging"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    FIRST_DEAL = "first_deal"
    GROWTH = "growth"
    # V1 保留兼容
    PLAN_PATH = "plan_path"
    TAKE_ACTION = "take_action"
    TROUBLESHOOT = "troubleshoot"
```

2. 新增模型类：
```python
class UserAssessment(BaseModel):
    digital_literacy: str  # basic / intermediate / advanced
    mental_readiness: str  # job_seeking / exploring / ready
    time_commitment: str  # <1h / 1-3h / >3h
    financial_pressure: str  # comfortable / moderate / urgent
    profile_tag: str
    content_pace: str  # slow / normal / fast
    first_milestone: str
    expectation_tone: str


class ContentWeek(BaseModel):
    week: int
    theme: str
    pieces: int
    status: str = "not_started"  # not_started / in_progress / completed
    generated_content: list[dict] = Field(default_factory=list)


class ContentPlan(BaseModel):
    platform: str
    total_pieces: int = 30
    weeks: list[ContentWeek] = Field(default_factory=list)
    paused: bool = False
    current_week: int = 1


class PhaseResult(BaseModel):
    phase: int
    data: dict = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
```

3. 扩展 `UserState` 新增字段：
```python
class UserState(BaseModel):
    # ... 保留现有字段 ...
    assessment: UserAssessment | None = None
    phase_results: dict[str, PhaseResult] = Field(default_factory=dict)
    content_plan: ContentPlan | None = None
```

**Step 4: 运行测试确认通过**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_models.py -v`
Expected: ALL PASS

**Step 5: 提交**

```bash
git add src/starting_point/models.py tests/test_models.py
git commit -m "feat: extend models for V2 6-phase journey"
```

---

## Task 2: 新增 PromptBuilder 模板

**Files:**
- Modify: `src/starting_point/llm/prompts.py`

**Step 1: 写失败测试**

```python
# tests/test_prompts.py (新建)
from starting_point.llm.prompts import PromptBuilder


def test_build_assessment_prompt():
    builder = PromptBuilder()
    prompt = builder.build_assessment_strategy_prompt(
        digital_literacy="basic",
        mental_readiness="job_seeking",
        time_commitment="<1h",
        financial_pressure="urgent",
    )
    assert "basic" in prompt or "新手" in prompt
    assert "策略" in prompt or "strategy" in prompt.lower()


def test_build_product_card_prompt():
    builder = PromptBuilder()
    prompt = builder.build_product_card_prompt(
        industry="建材",
        assets='[{"name":"选材能力","evidence":"15年经验"}]',
        assessment_tag="有基础+愿意试+低压力",
    )
    assert "建材" in prompt
    assert "服务" in prompt or "产品" in prompt


def test_build_content_plan_prompt():
    builder = PromptBuilder()
    prompt = builder.build_content_week_prompt(
        week=1,
        theme="试水期",
        industry="建材",
        platform="xiaohongshu",
        service_name="装修避坑顾问",
        pieces=7,
    )
    assert "7" in prompt
    assert "小红书" in prompt or "xiaohongshu" in prompt.lower()


def test_build_first_deal_prompt():
    builder = PromptBuilder()
    prompt = builder.build_first_deal_prompt(
        service_name="装修避坑顾问",
        pricing="体验价99元，正式价299-599元",
        service_flow="1.客户发报价单 2.标注关注点 3.30分钟沟通 4.出具建议清单",
    )
    assert "装修" in prompt
    assert "话术" in prompt or "模板" in prompt


def test_build_growth_prompt():
    builder = PromptBuilder()
    prompt = builder.build_growth_prompt(
        service_name="装修避坑顾问",
        first_deal_price=299,
        channel="xiaohongshu",
    )
    assert "涨价" in prompt or "转介绍" in prompt
```

**Step 2: 运行测试确认失败**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `build_assessment_strategy_prompt` not found

**Step 3: 在 PromptBuilder 中添加5个新模板方法**

在 `prompts.py` 的 `PromptBuilder` 类中添加：

```python
ASSESSMENT_STRATEGY_TEMPLATE = """你是启点的用户评估顾问。根据以下用户情况，生成个性化策略。

数字能力：{digital_literacy}
心理准备：{mental_readiness}
时间投入：{time_commitment}
经济压力：{financial_pressure}

请以JSON格式返回：
{{
  "profile_tag": "一个简短的标签，如'数字新手+心理犹豫+时间充裕+高压力'",
  "content_pace": "slow/normal/fast",
  "first_milestone": "第一个小目标",
  "expectation_tone": "期望管理话术",
  "strategy_summary": "3句话以内的策略建议"
}}"""

PRODUCT_CARD_TEMPLATE = """你是启点的产品包装顾问。根据用户的行业和资产，设计一个可以卖的服务产品。

行业：{industry}
可定价资产：{assets}
用户画像：{assessment_tag}

请以JSON格式返回一个服务产品卡片：
{{
  "service_name": "服务名称，要接地气",
  "tagline": "一句话定位",
  "target_customer": "目标客户描述",
  "pricing": {{
    "trial_price": "体验价（数字+单位）",
    "standard_price": "正式价区间",
    "package_price": "套餐价（如有）"
  }},
  "service_flow": ["步骤1", "步骤2", "步骤3", "步骤4"],
  "deliverables": "交付物描述",
  "tools_recommended": ["推荐工具1", "推荐工具2"]
}}"""

CONTENT_WEEK_TEMPLATE = """你是启点的内容策划师。为一个{industry}行业的用户，在小红书/抖音上生成第{week}周的内容。

周主题：{theme}
服务产品：{service_name}
目标平台：{platform}
本周需要生成：{pieces}条内容

请以JSON格式返回：
{{
  "week_theme": "本周主题",
  "emotional_support": "本周的情绪管理话术，真实不空洞",
  "content_pieces": [
    {{
      "day": 1,
      "type": "经验分享/避坑指南/故事/互动问答",
      "title": "标题",
      "script": "具体脚本或文案，可以直接用的",
      "tags": ["标签1", "标签2"]
    }}
  ],
  "next_week_hint": "下周方向建议"
}}"""

FIRST_DEAL_TEMPLATE = """你是启点的首单教练。根据用户的服务产品，生成完成首单所需的所有工具。

服务产品：{service_name}
定价：{pricing}
服务流程：{service_flow}

请以JSON格式返回：
{{
  "communication_templates": {{
    "price_inquiry": "客户问价时的回复话术",
    "service_inquiry": "客户问服务时的回复话术",
    "hesitant_client": "客户犹豫时的回复话术"
  }},
  "pricing_formula": "具体报价公式，带数字",
  "payment_methods": [
    {{"method": "方式名", "how": "怎么操作", "tip": "注意事项"}}
  ],
  "delivery_checklist": ["交付步骤1", "交付步骤2", "交付步骤3"],
  "post_delivery": "交付后引导客户反馈的话术"
}}"""

GROWTH_TEMPLATE = """你是启点的增长顾问。用户刚完成了首单，需要指导下一步。

服务产品：{service_name}
首单价格：{first_deal_price}元
获客渠道：{channel}

请以JSON格式返回：
{{
  "testimonial_to_content": "把客户好评变成内容的话术和方法",
  "pricing_adjustment": "什么时候涨价、涨多少的具体建议",
  "referral_mechanism": "转介绍的具体方案",
  "repeat_purchase": "复购产品设计建议"
}}"""

class PromptBuilder:
    # ... 保留现有方法 ...

    def build_assessment_strategy_prompt(self, digital_literacy: str, mental_readiness: str, time_commitment: str, financial_pressure: str) -> str:
        return self.ASSESSMENT_STRATEGY_TEMPLATE.format(
            digital_literacy=digital_literacy, mental_readiness=mental_readiness,
            time_commitment=time_commitment, financial_pressure=financial_pressure,
        )

    def build_product_card_prompt(self, industry: str, assets: str, assessment_tag: str) -> str:
        return self.PRODUCT_CARD_TEMPLATE.format(
            industry=industry, assets=assets, assessment_tag=assessment_tag,
        )

    def build_content_week_prompt(self, week: int, theme: str, industry: str, platform: str, service_name: str, pieces: int) -> str:
        return self.CONTENT_WEEK_TEMPLATE.format(
            week=week, theme=theme, industry=industry,
            platform=platform, service_name=service_name, pieces=pieces,
        )

    def build_first_deal_prompt(self, service_name: str, pricing: str, service_flow: str) -> str:
        return self.FIRST_DEAL_TEMPLATE.format(
            service_name=service_name, pricing=pricing, service_flow=service_flow,
        )

    def build_growth_prompt(self, service_name: str, first_deal_price: int, channel: str) -> str:
        return self.GROWTH_TEMPLATE.format(
            service_name=service_name, first_deal_price=first_deal_price, channel=channel,
        )
```

**Step 4: 运行测试确认通过**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_prompts.py -v`
Expected: ALL PASS

**Step 5: 提交**

```bash
git add src/starting_point/llm/prompts.py tests/test_prompts.py
git commit -m "feat: add V2 prompt templates for all 5 new phases"
```

---

## Task 3: AssessmentSkill（阶段0）

**Files:**
- Create: `src/starting_point/skills/assessment.py`
- Create: `tests/test_skills/test_assessment.py`

**Step 1: 写失败测试**

```python
# tests/test_skills/test_assessment.py
from starting_point.models import UserState
from starting_point.skills.assessment import AssessmentSkill


def test_skill_has_4_steps():
    skill = AssessmentSkill()
    assert skill.total_steps == 4


def test_first_step_is_digital_literacy():
    skill = AssessmentSkill()
    step = skill.get_step(0)
    assert step.id == "digital_literacy"


def test_process_answer_returns_next_step():
    skill = AssessmentSkill()
    state = UserState(user_id="test")
    result = skill.process_answer("digital_literacy", "basic", state)
    assert result.next_step is True


def test_generate_output_returns_strategy():
    skill = AssessmentSkill()
    state = UserState(user_id="test")
    # 填充4个步骤的结果
    for i, (sid, ans) in enumerate([
        ("digital_literacy", "basic"),
        ("mental_readiness", "exploring"),
        ("time_commitment", "1-3h"),
        ("financial_pressure", "moderate"),
    ]):
        state.step_results.append(
            __import__("starting_point.models", fromlist=["SkillStepResult"]).SkillStepResult(
                step_id=sid, answer=ans
            )
        )
    import asyncio
    output = asyncio.get_event_loop().run_until_complete(skill.generate_output(state))
    assert output["skill_type"] == "assessment"
    assert "profile_tag" in output or "answers" in output
```

**Step 2: 运行测试确认失败**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_assessment.py -v`
Expected: FAIL — module not found

**Step 3: 实现 AssessmentSkill**

```python
# src/starting_point/skills/assessment.py
from __future__ import annotations

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class AssessmentSkill(BaseSkill):
    name = "起跑评估"
    description = "评估你的起点，制定个性化策略"
    order = 0

    steps = [
        Step(
            id="digital_literacy",
            question="你平时用手机做什么？",
            options=[
                StepOption(label="打电话、发微信", value="basic"),
                StepOption(label="刷抖音、看小红书", value="intermediate"),
                StepOption(label="发过视频或帖子", value="advanced"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="mental_readiness",
            question="你现在最想的是什么？",
            options=[
                StepOption(label="找到一份工作", value="job_seeking"),
                StepOption(label="试试自己干", value="ready"),
                StepOption(label="不确定，想先看看", value="exploring"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="time_commitment",
            question="你每天能花多少时间在这件事上？",
            options=[
                StepOption(label="1小时以内", value="<1h"),
                StepOption(label="1到3小时", value="1-3h"),
                StepOption(label="3小时以上", value=">3h"),
            ],
        ),
        Step(
            id="financial_pressure",
            question="你现在的经济状况？",
            options=[
                StepOption(label="还有3个月以上缓冲", value="comfortable"),
                StepOption(label="1到3个月", value="moderate"),
                StepOption(label="一个月内很紧张", value="urgent"),
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
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        answers = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }

        if self._llm is None:
            return {"skill_type": "assessment", "answers": answers}

        prompt = self._prompt_builder.build_assessment_strategy_prompt(
            digital_literacy=answers.get("digital_literacy", "basic"),
            mental_readiness=answers.get("mental_readiness", "exploring"),
            time_commitment=answers.get("time_commitment", "1-3h"),
            financial_pressure=answers.get("financial_pressure", "moderate"),
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的用户评估顾问。",
        )
        return {"skill_type": "assessment", "answers": answers, "strategy": self._parse_json(raw)}

    def _parse_json(self, text: str) -> dict:
        import json
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"raw": text}
```

**Step 4: 运行测试确认通过**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/test_skills/test_assessment.py -v`
Expected: ALL PASS

**Step 5: 提交**

```bash
git add src/starting_point/skills/assessment.py tests/test_skills/test_assessment.py
git commit -m "feat: add AssessmentSkill (phase 0)"
```

---

## Task 4: ProductPackagingSkill（阶段2）

**Files:**
- Create: `src/starting_point/skills/product_packaging.py`
- Create: `tests/test_skills/test_product_packaging.py`

**Step 1: 写失败测试**

```python
# tests/test_skills/test_product_packaging.py
from starting_point.models import UserState
from starting_point.skills.product_packaging import ProductPackagingSkill


def test_skill_has_steps():
    skill = ProductPackagingSkill()
    assert skill.total_steps >= 3


def test_first_step_is_service_format():
    skill = ProductPackagingSkill()
    step = skill.get_step(0)
    assert step.id == "service_format"


def test_process_answer_returns_next_step():
    skill = ProductPackagingSkill()
    state = UserState(user_id="test")
    result = skill.process_answer("service_format", "一对一咨询", state)
    assert result.next_step is True
```

**Step 2: 运行测试确认失败**

**Step 3: 实现 ProductPackagingSkill**

```python
# src/starting_point/skills/product_packaging.py
from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class ProductPackagingSkill(BaseSkill):
    name = "包装产品"
    description = "把你的经验包装成可以卖的服务"
    order = 2

    steps = [
        Step(
            id="service_format",
            question="你最舒服的服务方式是什么？",
            options=[
                StepOption(label="一对一电话/视频咨询", value="consultation"),
                StepOption(label="出一份报告/清单", value="report"),
                StepOption(label="陪跑（全程跟着一个客户）", value="coaching"),
                StepOption(label="都不确定，帮我选", value="auto"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="target_customer",
            question="你觉得谁最需要你的经验？谁会愿意付钱？",
            options=[
                StepOption(label="正在装修的业主", value="homeowner"),
                StepOption(label="刚入行的新手", value="newcomer"),
                StepOption(label="小装修公司", value="small_company"),
                StepOption(label="我不确定", value="unsure"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="pricing_comfort",
            question="提到收钱，你最担心什么？",
            options=[
                StepOption(label="不知道该收多少", value="dont_know_price"),
                StepOption(label="怕别人觉得贵", value="afraid_expensive"),
                StepOption(label="不好意思收钱", value="uncomfortable"),
                StepOption(label="担心收了钱做不好", value="fear_delivery"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_product",
            question="我帮你设计了一个服务产品，看看是不是你想要的？如果有想改的，直接告诉我。",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        constraints = {
            r.step_id: r.free_text or r.answer
            for r in state.step_results
        }

        # 从上一个阶段获取资产和行业
        phase1_result = state.phase_results.get("1")
        assets = phase1_result.data.get("asset_map", {}) if phase1_result else {}
        industry = state.industry or "未知行业"

        if self._llm is None:
            return {"skill_type": "product_packaging", "constraints": constraints}

        assets_str = json.dumps(assets, ensure_ascii=False) if isinstance(assets, dict) else str(assets)
        assessment_tag = ""
        if state.assessment:
            assessment_tag = state.assessment.profile_tag

        prompt = self._prompt_builder.build_product_card_prompt(
            industry=industry, assets=assets_str, assessment_tag=assessment_tag,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的产品包装顾问。",
        )
        return {"skill_type": "product_packaging", "constraints": constraints, "product_card": self._parse_json(raw)}

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"raw": text}
```

**Step 4: 运行测试确认通过**

**Step 5: 提交**

```bash
git add src/starting_point/skills/product_packaging.py tests/test_skills/test_product_packaging.py
git commit -m "feat: add ProductPackagingSkill (phase 2)"
```

---

## Task 5: CustomerAcquisitionSkill（阶段3 — 30天内容计划）

**Files:**
- Create: `src/starting_point/skills/customer_acquisition.py`
- Create: `tests/test_skills/test_customer_acquisition.py`

**Step 1: 写失败测试**

```python
# tests/test_skills/test_customer_acquisition.py
from starting_point.models import UserState
from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill


def test_skill_has_steps():
    skill = CustomerAcquisitionSkill()
    assert skill.total_steps >= 2


def test_first_step_is_platform():
    skill = CustomerAcquisitionSkill()
    step = skill.get_step(0)
    assert step.id == "platform_choice"


def test_platform_options_include_douyin_and_xiaohongshu():
    skill = CustomerAcquisitionSkill()
    step = skill.get_step(0)
    values = [o.value for o in step.options]
    assert "douyin" in values
    assert "xiaohongshu" in values


def test_process_answer_returns_next_step():
    skill = CustomerAcquisitionSkill()
    state = UserState(user_id="test")
    result = skill.process_answer("platform_choice", "douyin", state)
    assert result.next_step is True
```

**Step 2: 运行测试确认失败**

**Step 3: 实现 CustomerAcquisitionSkill**

```python
# src/starting_point/skills/customer_acquisition.py
from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState

PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "wechat_moments": "朋友圈",
    "multi": "多平台同时",
}

WEEK_THEMES = [
    {"week": 1, "theme": "试水期", "pieces": 7},
    {"week": 2, "theme": "找感觉期", "pieces": 7},
    {"week": 3, "theme": "突破期", "pieces": 8},
    {"week": 4, "theme": "收获期", "pieces": 8},
]


class CustomerAcquisitionSkill(BaseSkill):
    name = "找到客户"
    description = "30天内容计划，帮你获得第一个咨询"
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
            question="我帮你制定了一个30天内容计划。第一周的内容已经准备好了，你可以先看看。准备好了就开始吧！",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(
        self, step_id: str, answer: str, state: UserState,
    ) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        platform_result = next(
            (r for r in state.step_results if r.step_id == "platform_choice"), None,
        )
        platform_key = (platform_result.free_text or platform_result.answer) if platform_result else "xiaohongshu"
        platform_name = PLATFORM_NAMES.get(platform_key, platform_key)

        # 获取阶段2的产品信息
        phase2_result = state.phase_results.get("2")
        service_name = ""
        if phase2_result:
            card = phase2_result.data.get("product_card", {})
            service_name = card.get("service_name", "")

        if self._llm is None:
            return {"skill_type": "customer_acquisition", "platform": platform_name, "status": "plan_generated"}

        # 生成第1周内容
        week_info = WEEK_THEMES[0]
        prompt = self._prompt_builder.build_content_week_prompt(
            week=week_info["week"],
            theme=week_info["theme"],
            industry=state.industry or "未知",
            platform=platform_name,
            service_name=service_name,
            pieces=week_info["pieces"],
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的内容策划师。",
        )
        return {
            "skill_type": "customer_acquisition",
            "platform": platform_name,
            "week1_content": self._parse_json(raw),
            "remaining_weeks": WEEK_THEMES[1:],
        }

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"raw": text}
```

**Step 4: 运行测试确认通过**

**Step 5: 提交**

```bash
git add src/starting_point/skills/customer_acquisition.py tests/test_skills/test_customer_acquisition.py
git commit -m "feat: add CustomerAcquisitionSkill (phase 3, 30-day content plan)"
```

---

## Task 6: FirstDealSkill（阶段4）+ GrowthSkill（阶段5）

这两个 Skill 结构类似，一起实现。

**Files:**
- Create: `src/starting_point/skills/first_deal.py`
- Create: `src/starting_point/skills/growth.py`
- Create: `tests/test_skills/test_first_deal.py`
- Create: `tests/test_skills/test_growth.py`

**Step 1: 写失败测试**

```python
# tests/test_skills/test_first_deal.py
from starting_point.models import UserState
from starting_point.skills.first_deal import FirstDealSkill


def test_skill_has_steps():
    skill = FirstDealSkill()
    assert skill.total_steps >= 2


def test_first_step_is_customer_status():
    skill = FirstDealSkill()
    step = skill.get_step(0)
    assert step.id == "customer_status"


# tests/test_skills/test_growth.py
from starting_point.models import UserState
from starting_point.skills.growth import GrowthSkill


def test_skill_has_steps():
    skill = GrowthSkill()
    assert skill.total_steps >= 2


def test_first_step_is_deal_status():
    skill = GrowthSkill()
    step = skill.get_step(0)
    assert step.id == "deal_status"
```

**Step 2: 运行测试确认失败**

**Step 3: 实现两个 Skill**

FirstDealSkill — 3步（客户状态 → 确认准备 → 完成）：

```python
# src/starting_point/skills/first_deal.py
from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class FirstDealSkill(BaseSkill):
    name = "完成首单"
    description = "客户来了，教你搞定第一单"
    order = 4

    steps = [
        Step(
            id="customer_status",
            question="客户来了！现在是什么情况？",
            options=[
                StepOption(label="有人在私信问我了", value="inquiry"),
                StepOption(label="有人问价格了", value="price_asked"),
                StepOption(label="有人想约咨询了", value="wants_consultation"),
                StepOption(label="还没有客户，先学学", value="no_customer_yet"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_tools",
            question="我已经帮你准备好了沟通话术、报价公式和交付清单。仔细看看，有不懂的随时问我。",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(self, step_id: str, answer: str, state: UserState) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        phase2 = state.phase_results.get("2")
        product_card = phase2.data.get("product_card", {}) if phase2 else {}
        service_name = product_card.get("service_name", "")
        pricing = json.dumps(product_card.get("pricing", {}), ensure_ascii=False)
        service_flow = "\n".join(product_card.get("service_flow", []))

        if self._llm is None:
            return {"skill_type": "first_deal", "product_card": product_card}

        prompt = self._prompt_builder.build_first_deal_prompt(
            service_name=service_name, pricing=pricing, service_flow=service_flow,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的首单教练。",
        )
        return {"skill_type": "first_deal", "toolkit": self._parse_json(raw)}

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"raw": text}
```

GrowthSkill — 2步（首单完成确认 → 增长计划）：

```python
# src/starting_point/skills/growth.py
from __future__ import annotations

import json

from starting_point.engine.skill_base import BaseSkill, StepResult
from starting_point.llm.client import DeepSeekClient
from starting_point.llm.prompts import PromptBuilder
from starting_point.models import Step, StepOption, UserState


class GrowthSkill(BaseSkill):
    name = "转起来"
    description = "首单之后，持续赚钱"
    order = 5

    steps = [
        Step(
            id="deal_status",
            question="恭喜！第一单完成了吗？",
            options=[
                StepOption(label="完成了！客户很满意", value="completed"),
                StepOption(label="完成了，但有点波折", value="completed_bumpy"),
                StepOption(label="还没完成，还在沟通中", value="in_progress"),
            ],
            allow_free_text=True,
        ),
        Step(
            id="confirm_growth",
            question="这是你的增长计划。从今天开始，你不再是一个失业的人了——你是一个有自己的小生意的人。",
        ),
    ]

    def __init__(self, llm_client: DeepSeekClient | None = None) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()

    def process_answer(self, step_id: str, answer: str, state: UserState) -> StepResult:
        return StepResult(next_step=True)

    async def generate_output(self, state: UserState) -> dict:
        phase2 = state.phase_results.get("2")
        product_card = phase2.data.get("product_card", {}) if phase2 else {}
        service_name = product_card.get("service_name", "")
        first_deal_price = 0
        phase4 = state.phase_results.get("4")
        if phase4:
            toolkit = phase4.data.get("toolkit", {})
            first_deal_price = toolkit.get("first_deal_price", 0)

        # 从阶段3获取渠道
        channel = "xiaohongshu"
        phase3 = state.phase_results.get("3")
        if phase3:
            channel = phase3.data.get("platform", channel)

        if self._llm is None:
            return {"skill_type": "growth", "service_name": service_name}

        prompt = self._prompt_builder.build_growth_prompt(
            service_name=service_name,
            first_deal_price=first_deal_price or 299,
            channel=channel,
        )
        raw = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="你是启点的增长顾问。",
        )
        return {"skill_type": "growth", "growth_plan": self._parse_json(raw)}

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"raw": text}
```

**Step 4: 运行测试确认通过**

**Step 5: 提交**

```bash
git add src/starting_point/skills/first_deal.py src/starting_point/skills/growth.py tests/test_skills/test_first_deal.py tests/test_skills/test_growth.py
git commit -m "feat: add FirstDealSkill (phase 4) and GrowthSkill (phase 5)"
```

---

## Task 7: 更新 Runner 和 StateManager

**Files:**
- Modify: `src/starting_point/engine/runner.py`
- Modify: `src/starting_point/engine/state.py`
- Modify: `src/starting_point/main.py`
- Create: `tests/test_engine/test_v2_runner.py`

**Step 1: 写失败测试**

```python
# tests/test_engine/test_v2_runner.py
import asyncio
import pytest
from starting_point.engine.registry import SkillRegistry
from starting_point.engine.runner import SkillRunner
from starting_point.engine.state import StateManager
from starting_point.models import SkillType, UserState
from starting_point.skills.assessment import AssessmentSkill
from starting_point.skills.self_discovery import SelfDiscoverySkill


@pytest.fixture
def v2_runner(tmp_path):
    registry = SkillRegistry()
    registry.register(SkillType.ASSESSMENT, AssessmentSkill())
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill())
    sm = StateManager(tmp_path / "test.db")
    asyncio.get_event_loop().run_until_complete(sm.initialize())
    return SkillRunner(registry, sm, None)


def test_runner_starts_with_assessment(v2_runner):
    """V2 用户从阶段0开始。"""
    result = asyncio.get_event_loop().run_until_complete(
        v2_runner.process_message("v2user", "你好", None)
    )
    assert result.message.step_id == "digital_literacy"


def test_runner_advances_through_assessment(v2_runner):
    """完成阶段0后自动进入阶段1。"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(v2_runner.process_message("v2user", "你好", None))
    loop.run_until_complete(v2_runner.process_message("v2user", "basic", "basic"))
    loop.run_until_complete(v2_runner.process_message("v2user", "exploring", "exploring"))
    loop.run_until_complete(v2_runner.process_message("v2user", "1-3h", "1-3h"))
    result = loop.run_until_complete(v2_runner.process_message("v2user", "moderate", "moderate"))
    # 阶段0完成后应该进入阶段1
    assert "industry" in result.message.step_id or result.skill_completed
```

**Step 2: 运行测试确认失败**

**Step 3: 更新 Runner**

在 `runner.py` 中修改 `process_message` 以支持阶段自动切换：

关键改动：
1. 新用户从 `SkillType.ASSESSMENT` 开始（order=0）
2. 当一个 Skill 的最后一步完成时，自动切换到下一个 Skill
3. `go_back` 支持跨阶段回退
4. 保存阶段产出到 `state.phase_results`

```python
# runner.py 中修改的核心逻辑
async def process_message(self, user_id, message, selected_option):
    state = await self._get_or_create_state(user_id)

    # V2: 新用户从 ASSESSMENT 开始
    if not state.started:
        state.started = True
        first_skill_type = self._get_first_skill_type()
        state.current_skill = first_skill_type
        await self.state_manager.save_state(state)
        skill = self.registry.get(first_skill_type)
        step = skill.get_step(0)
        return self._build_step_response(step, 0, skill.total_steps)

    skill = self.registry.get(state.current_skill)
    step = skill.get_step(state.current_step_index)

    # 记录答案
    result_record = SkillStepResult(...)
    state.step_results.append(result_record)
    result = skill.process_answer(step.id, message, state)

    if result.next_step:
        state.completed_steps.append(step.id)
        next_index = state.current_step_index + 1

        if next_index >= skill.total_steps:
            # 当前阶段完成 — 保存产出，切换到下一阶段
            output = await skill.generate_output(state)
            state.phase_results[str(skill.order)] = PhaseResult(
                phase=skill.order, data=output,
            )
            next_skill = self._get_next_skill(skill.order)
            if next_skill:
                state.current_skill = self._get_skill_type_for_skill(next_skill)
                state.current_step_index = 0
                state.step_results = []
                state.completed_steps = []
                skill = next_skill
            else:
                # 全部完成
                await self.state_manager.save_state(state)
                return ChatResponse(...)
        else:
            state.current_step_index = next_index

    await self.state_manager.save_state(state)
    ...
```

**Step 4: 更新 main.py 注册所有新 Skill**

```python
from starting_point.skills.assessment import AssessmentSkill
from starting_point.skills.product_packaging import ProductPackagingSkill
from starting_point.skills.customer_acquisition import CustomerAcquisitionSkill
from starting_point.skills.first_deal import FirstDealSkill
from starting_point.skills.growth import GrowthSkill

def create_registry(llm_client=None):
    registry = SkillRegistry()
    registry.register(SkillType.ASSESSMENT, AssessmentSkill(llm_client))
    registry.register(SkillType.SELF_DISCOVERY, SelfDiscoverySkill(llm_client))
    registry.register(SkillType.PRODUCT_PACKAGING, ProductPackagingSkill(llm_client))
    registry.register(SkillType.CUSTOMER_ACQUISITION, CustomerAcquisitionSkill(llm_client))
    registry.register(SkillType.FIRST_DEAL, FirstDealSkill(llm_client))
    registry.register(SkillType.GROWTH, GrowthSkill(llm_client))
    return registry
```

**Step 5: 运行测试确认通过**

**Step 6: 提交**

```bash
git add src/starting_point/engine/runner.py src/starting_point/engine/state.py src/starting_point/main.py tests/test_engine/test_v2_runner.py
git commit -m "feat: update runner for V2 multi-phase flow with auto-advance"
```

---

## Task 8: 新增 API 端点

**Files:**
- Modify: `src/starting_point/main.py`
- Create: `tests/test_api.py`

新增端点：

1. `POST /api/pause/{user_id}` — 暂停当前阶段（主要是阶段3内容计划）
2. `POST /api/resume/{user_id}` — 恢复暂停的阶段
3. `POST /api/reassess/{user_id}` — 重新跑阶段0评估
4. `GET /api/content-plan/{user_id}` — 获取30天内容计划进度
5. `POST /api/content-week/{user_id}/{week}` — 生成指定周的内容

每个端点按 TDD 模式实现：写测试 → 确认失败 → 实现 → 确认通过 → 提交。

最终提交：
```bash
git commit -m "feat: add V2 API endpoints for pause/resume/reassess/content-plan"
```

---

## Task 9: 确保 V1 测试不回归

**Files:**
- Modify: 现有测试文件如果需要

**Step 1: 运行完整测试套件**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m pytest tests/ -v`
Expected: ALL PASS（V1 的所有测试在 V2 下仍然通过）

**Step 2: 如果有失败，修复并提交**

```bash
git commit -m "fix: ensure V1 tests pass with V2 changes"
```

---

## Task 10: 端到端验证

**Step 1: 启动服务器**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && SP_DEEPSEEK_API_KEY=$(grep SP_DEEPSEEK_API_KEY .env | cut -d= -f2) python -m starting_point.main`

**Step 2: 用 curl 测试完整流程**

```bash
# 阶段0: 开始评估
curl -s -X POST http://127.0.0.1:8768/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"e2e-test","message":"你好","selected_option":null}'

# 阶段0: 4步评估
curl -s -X POST http://127.0.0.1:8768/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"e2e-test","message":"basic","selected_option":"basic"}'
# ... 继续完成4步

# 确认自动进入阶段1
# 确认阶段1完成后自动进入阶段2
# 确认所有6个阶段可以顺序走完
```

**Step 3: 提交最终状态**

```bash
git commit -m "chore: V2 implementation complete, all phases working"
```

---

## 实施顺序总结

| Task | 描述 | 依赖 | 估计时间 |
|------|------|------|---------|
| 1 | 扩展数据模型 | 无 | 15min |
| 2 | PromptBuilder 模板 | 无 | 15min |
| 3 | AssessmentSkill | Task 1 | 15min |
| 4 | ProductPackagingSkill | Task 1, 2 | 15min |
| 5 | CustomerAcquisitionSkill | Task 1, 2 | 20min |
| 6 | FirstDealSkill + GrowthSkill | Task 1, 2 | 20min |
| 7 | 更新 Runner + StateManager | Task 1-6 | 30min |
| 8 | 新增 API 端点 | Task 7 | 20min |
| 9 | V1 回归测试 | Task 7 | 10min |
| 10 | 端到端验证 | Task 1-9 | 15min |

**总计：约 2.5 小时**

Task 1-2 可以并行。Task 3-6 可以并行。Task 7 依赖 1-6。Task 8-10 串行。
