from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_knowledge_point_valid():
    from starting_point.models import KnowledgePoint

    kp = KnowledgePoint(
        id="kp_1",
        description="建材价格套利：品牌瓷砖80元 vs 平替35元",
        industry="建材",
        knowledge_type="price_transparency",
        target_buyer="预算紧张的装修业主",
        estimated_value="帮100平装修省5000-10000元",
    )
    assert kp.id == "kp_1"


def test_knowledge_point_rejects_bad_id():
    from starting_point.models import KnowledgePoint

    with pytest.raises(ValidationError):
        KnowledgePoint(
            id="bad_id",
            description="x" * 10,
            industry="test",
            knowledge_type="price_transparency",
            target_buyer="buyers",
            estimated_value="saves money",
        )


def test_knowledge_point_rejects_short_description():
    from starting_point.models import KnowledgePoint

    with pytest.raises(ValidationError):
        KnowledgePoint(
            id="kp_1",
            description="short",
            industry="test",
            knowledge_type="price_transparency",
            target_buyer="buyers",
            estimated_value="saves money",
        )


def test_stage_zero_output_rejects_less_than_3_points():
    from starting_point.models import KnowledgePoint, StageZeroOutput

    kps = [
        KnowledgePoint(
            id=f"kp_{i}",
            description="A valid knowledge point description here",
            industry="test",
            knowledge_type="price_transparency",
            target_buyer="some target buyer group",
            estimated_value="saves some amount of money",
        )
        for i in range(1, 3)
    ]
    with pytest.raises(ValidationError):
        StageZeroOutput(knowledge_points=kps, summary="Found some points")


def test_stage_zero_output_accepts_3_points():
    from starting_point.models import KnowledgePoint, StageZeroOutput

    kps = [
        KnowledgePoint(
            id=f"kp_{i}",
            description="A valid knowledge point description here",
            industry="test",
            knowledge_type="price_transparency",
            target_buyer="some target buyer group",
            estimated_value="saves some amount of money",
        )
        for i in range(1, 4)
    ]
    result = StageZeroOutput(knowledge_points=kps, summary="Found several points about knowledge")
    assert len(result.knowledge_points) == 3


def test_product_package_valid():
    from starting_point.models import ProductPackage

    pkg = ProductPackage(
        selected_knowledge_id="kp_1",
        product_name="装修材料省钱咨询",
        one_liner="10年建材老兵帮你审材料清单，帮你省30%",
        target_buyer="正在装修、预算紧张的业主",
        service_type="consultation",
        price_range={"min": 49, "max": 199, "currency": "CNY"},
        delivery_method="微信语音/文字咨询，24小时内回复",
    )
    assert pkg.service_type == "consultation"


def test_product_package_rejects_invalid_service_type():
    from starting_point.models import ProductPackage

    with pytest.raises(ValidationError):
        ProductPackage(
            selected_knowledge_id="kp_1",
            product_name="test",
            one_liner="test one liner",
            target_buyer="test buyers",
            service_type="invalid_type",
            price_range={"min": 10, "max": 100, "currency": "CNY"},
            delivery_method="test delivery",
        )


def test_chat_request_validates_message_length():
    from starting_point.models import ChatRequest

    req = ChatRequest(user_id="user1", message="你好")
    assert req.message == "你好"

    with pytest.raises(ValidationError):
        ChatRequest(user_id="user1", message="")

    with pytest.raises(ValidationError):
        ChatRequest(user_id="user1", message="x" * 501)
