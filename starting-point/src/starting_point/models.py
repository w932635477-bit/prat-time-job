from __future__ import annotations

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


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=2, max_length=500)


class ChatResponse(BaseModel):
    message: str
    stage: int
    stage_data: dict = Field(default_factory=dict)
    is_complete: bool = False
