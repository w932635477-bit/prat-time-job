from starting_point.confidence.engine import ConfidenceEngine
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
