from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field


class KnowledgePoint(BaseModel):
    id: str = Field(pattern=r"^kp_\d+$")
    description: str = Field(min_length=10)
    industry: str = Field(min_length=1)
    knowledge_type: Literal[
        "price_transparency",
        "pitfall_guide",
        "channel_info",
        "industry_insider",
    ]
    target_buyer: str = Field(min_length=5)
    estimated_value: str = Field(min_length=5)


class StageZeroOutput(BaseModel):
    knowledge_points: list[KnowledgePoint] = Field(min_length=3)
    summary: str = Field(min_length=20)


class PriceRange(BaseModel):
    min: int = Field(ge=0)
    max: int = Field(ge=0)
    currency: str = Field(default="CNY")

    def model_post_init(self, __context: object) -> None:
        if self.min > self.max:
            raise ValueError(f"min ({self.min}) must be <= max ({self.max})")


class ProductPackage(BaseModel):
    selected_knowledge_id: str = Field(pattern=r"^kp_\d+$")
    product_name: str = Field(min_length=2)
    one_liner: str = Field(min_length=5)
    target_buyer: str = Field(min_length=5)
    service_type: Literal["consultation", "content", "service"]
    price_range: PriceRange
    delivery_method: str = Field(min_length=5)


class PlatformRecommendation(BaseModel):
    platform: str
    priority: int = Field(ge=1)
    reason: str = Field(min_length=5)
    content_format: str = Field(min_length=2)


class NextStep(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    auto_prompt: str = Field(min_length=1)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=2, max_length=500)


class ChatResponse(BaseModel):
    message: str | ChatMessage = ""
    stage: int = 0
    stage_data: dict = Field(default_factory=dict)
    is_complete: bool = False
    progress: float = 0.0
    skill_completed: bool = False
    output: dict | None = None
    current_step: int = 0
    next_step: NextStep | None = None


class User(BaseModel):
    id: str
    wx_openid: str | None = None
    wx_unionid: str = ""
    nickname: str = ""
    avatar_url: str = ""
    phone: str = ""
    tier: str = "free"
    tier_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Order(BaseModel):
    id: str
    user_id: str
    tier: str
    amount: int
    wx_prepay_id: str = ""
    wx_transaction_id: str = ""
    status: str = "pending"
    paid_at: datetime | None = None
    created_at: datetime | None = None


TIER_DEFINITIONS: dict[str, dict] = {
    "free": {"label": "免费体验", "price_fen": 0, "duration_days": 0},
    "standard": {"label": "完整方案包 ¥29", "price_fen": 2900, "duration_days": 60},
    "human": {"label": "真人教练加持 ¥199", "price_fen": 19900, "duration_days": 60},
}


class UserProfile(BaseModel):
    user_id: str
    industry: str = ""
    years_experience: int = 0
    goals: str = ""
    updated_at: datetime | None = None


class SkillType(IntEnum):
    ASSESSMENT = 0
    SELF_DISCOVERY = 1
    PRODUCT_PACKAGING = 2
    CUSTOMER_ACQUISITION = 3
    FIRST_DEAL = 4
    GROWTH = 5
    PLAN_PATH = 6
    TROUBLESHOOT = 7


class ConfidenceLevel(str):
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


class SkillStepResult(BaseModel):
    step_id: str
    answer: str
    selected_option: str | None = None
    free_text: str | None = None


class SkillOutput(BaseModel):
    skill_type: SkillType
    data: dict = Field(default_factory=dict)
    summary: str = ""


class PhaseResult(BaseModel):
    phase: int
    data: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str = "assistant"
    content: str = ""
    options: list[StepOption] | None = None
    allow_free_text: bool = True
    step_id: str | None = None
    confidence_boost: str | None = None


class UserAssessment(BaseModel):
    digital_literacy: str = ""
    mental_readiness: str = ""
    time_commitment: str = ""
    financial_pressure: str = ""
    profile_tag: str = ""
    content_pace: str = ""
    first_milestone: str = ""
    expectation_tone: str = ""


class CapabilityItem(BaseModel):
    name: str = ""
    description: str = ""
    evidence: str = ""
    estimated_value: str | None = None


class AssetMap(BaseModel):
    capabilities: list[CapabilityItem] = Field(default_factory=list)
    market_signals: MarketSignals | dict | None = None


class MarketSignals(BaseModel):
    demand_evidence: str = ""
    search_intent: str = ""
    shared_pain_point: str = ""
    market_readiness: str = ""


class TaskDay(BaseModel):
    day: int = 0
    task: str = ""
    platform: str = ""
    estimated_time: str = ""
    why: str = ""
    success_signal: str = ""
    status: str = "active"
    stuck_reason: str | None = None
    completed_at: datetime | None = None


class TaskPlan(BaseModel):
    total_days: int = 0
    current_day: int = 1
    days: list[TaskDay] = Field(default_factory=list)
    tasks: list[TaskDay] = Field(default_factory=list)
    platform: str = ""
    status: str = "active"


class UserState(BaseModel):
    user_id: str
    current_skill: SkillType = SkillType.ASSESSMENT
    current_step_index: int = 0
    started: bool = False
    step_results: list[SkillStepResult] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)
    phase_results: dict[str, PhaseResult] = Field(default_factory=dict)
    task_plan: TaskPlan | None = None
    assessment: UserAssessment | None = None
    asset_map: AssetMap | None = None
    recommended_creators: list[int] = Field(default_factory=list)


class CreatorExample(BaseModel):
    id: int
    account_name: str
    douyin_id: str = ""
    category: str
    sub_category: str = ""
    follower_tier: str = ""
    monetization_methods: list[str] = Field(default_factory=list)
    origin_story: str = ""
    user_profile_tags: list[str] = Field(default_factory=list)
    content_style: str = ""
    is_active: bool = True


# Aliases for backward compatibility with tests
DailyTask = TaskDay
DailyTaskPlan = TaskPlan
