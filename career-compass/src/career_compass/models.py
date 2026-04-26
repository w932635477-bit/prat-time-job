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
    started: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


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
