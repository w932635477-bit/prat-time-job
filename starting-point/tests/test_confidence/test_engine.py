from starting_point.confidence.engine import ConfidenceEngine
from starting_point.models import ConfidenceLevel


def test_detect_negative_emotion():
    engine = ConfidenceEngine()
    assert engine.detect_negative_emotion("我不行，什么都不懂")
    assert engine.detect_negative_emotion("没什么用，都是过去的事了")
    assert engine.detect_negative_emotion("算了，我不想做了")
    assert not engine.detect_negative_emotion("我在建材行业干了12年")


def test_detect_negative_emotion_no_false_positives():
    engine = ConfidenceEngine()
    assert not engine.detect_negative_emotion("我算了一下大概能赚5000")
    assert not engine.detect_negative_emotion("养老贷款利率")
    assert not engine.detect_negative_emotion("明白费率的计算方法")
    assert not engine.detect_negative_emotion("我不敢说绝对，但这个价格确实合理")


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


def test_detect_helplessness():
    engine = ConfidenceEngine()
    assert engine.detect_helplessness("不会拍视频")
    assert engine.detect_helplessness("不知道怎么开始")
    assert engine.detect_helplessness("从哪开始")
    assert engine.detect_helplessness("没拍过视频，不知道怎么做")
    assert engine.detect_helplessness("不会用手机拍")


def test_detect_helplessness_no_false_positives():
    engine = ConfidenceEngine()
    assert not engine.detect_helplessness("我拍了一个视频发到抖音上了")
    assert not engine.detect_helplessness("做了20年厨师了")
    assert not engine.detect_helplessness("开始之前先聊聊你的经验")
