from __future__ import annotations

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class SkillType(str, Enum):
    # V2 phases (ordered 0-5)
    ASSESSMENT = "assessment"
    SELF_DISCOVERY = "self_discovery"
    PRODUCT_PACKAGING = "product_packaging"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    FIRST_DEAL = "first_deal"
    GROWTH = "growth"
    # V1 backward compat
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


class MarketSignals(BaseModel):
    demand_evidence: str = ""
    search_intent: str = ""
    shared_pain_point: str = ""
    market_readiness: str = "medium"


class AssetMap(BaseModel):
    capabilities: list[CapabilityItem] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    raw_stories: list[str] = Field(default_factory=list)
    market_signals: MarketSignals | None = None


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


class UserAssessment(BaseModel):
    digital_literacy: str = ""
    mental_readiness: str = ""
    time_commitment: str = ""
    financial_pressure: str = ""
    profile_tag: str = ""
    content_pace: str = "normal"
    first_milestone: str = ""
    expectation_tone: str = ""


class ContentWeek(BaseModel):
    week: int
    theme: str
    pieces: int
    status: str = "not_started"
    generated_content: list[dict] = Field(default_factory=list)


class ContentPlan(BaseModel):
    platform: str = "xiaohongshu"
    total_pieces: int = 30
    weeks: list[ContentWeek] = Field(default_factory=list)
    paused: bool = False
    current_week: int = 1


class PhaseResult(BaseModel):
    phase: int
    data: dict = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


class UserState(BaseModel):
    user_id: str
    current_skill: SkillType = SkillType.ASSESSMENT
    current_step_index: int = 0
    completed_steps: list[str] = Field(default_factory=list)
    step_results: list[SkillStepResult] = Field(default_factory=list)
    asset_map: AssetMap | None = None
    selected_offer: OfferItem | None = None
    launched: bool = False
    started: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    # V2 fields
    assessment: UserAssessment | None = None
    phase_results: dict[str, PhaseResult] = Field(default_factory=dict)
    content_plan: ContentPlan | None = None


class ChatMessage(BaseModel):
    role: str
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
    progress: float
    deliverable: SkillOutput | None = None
    skill_completed: bool = False
    output: dict | None = None
    current_step: int | None = None


class User(BaseModel):
    id: str
    wx_openid: str
    wx_unionid: str = ""
    nickname: str = ""
    avatar_url: str = ""
    phone: str = ""
    tier: str = "free"
    tier_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Order(BaseModel):
    id: str
    user_id: str
    tier: str
    amount: int  # price in fen (cents)
    wx_prepay_id: str = ""
    wx_transaction_id: str = ""
    status: str = "pending"
    paid_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class UserProfile(BaseModel):
    user_id: str
    industry: str = ""
    years_experience: int = 0
    goals: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


TIER_DEFINITIONS: dict[str, dict] = {
    "free": {
        "label": "免费体验",
        "price_fen": 0,
        "description": "Phase 0 + Phase 1 + Phase 2 预览",
        "duration_days": None,
    },
    "low_ticket": {
        "label": "产品包装",
        "price_fen": 1990,
        "description": "完整 Phase 2（产品包装 + 定价）",
        "duration_days": 60,
    },
    "standard": {
        "label": "完整方案",
        "price_fen": 5900,
        "description": "Phase 2-5 全部（包装 + 获客 + 首单 + 增长）",
        "duration_days": 60,
    },
    "human": {
        "label": "人工辅导",
        "price_fen": 19900,
        "description": "完整方案 + 一次人工审核 + 微信群答疑30天",
        "duration_days": 90,
    },
}


class PaywallResponse(BaseModel):
    paywall: bool = True
    preview_data: dict = Field(default_factory=dict)
    tiers: list[dict] = Field(default_factory=list)
