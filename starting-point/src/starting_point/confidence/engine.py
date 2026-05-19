from __future__ import annotations

from starting_point.confidence.patterns import NEGATIVE_PATTERNS_COMPILED
from starting_point.models import ConfidenceLevel


class ConfidenceEngine:
    def detect_negative_emotion(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in NEGATIVE_PATTERNS_COMPILED)

    def assess_from_answer(self, answer: str) -> ConfidenceLevel:
        if len(answer) < 10:
            return ConfidenceLevel.LOW
        has_specific_number = any(c.isdigit() for c in answer)
        has_detail = any(
            kw in answer
            for kw in ["帮", "省", "避", "解决", "客户", "项目", "经历",
                       "问", "找我", "搜", "咨询", "坑", "被坑", "骗"]
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
