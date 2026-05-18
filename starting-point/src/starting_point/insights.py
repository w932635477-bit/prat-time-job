"""Extract actionable insights from completed conversations and log to JSONL.

After each Stage 1 completion, the LLM extracts new industry keywords,
monetization methods, pricing data, and delivery methods that aren't in the
wiki yet. A weekly review script aggregates these for human审核.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from starting_point.llm.client import LLMClient
from starting_point.wiki import HINTS

logger = logging.getLogger(__name__)

_INSIGHTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "insights"

EXTRACT_INSIGHT_PROMPT = """\
你是一个知识提取专家。从以下对话中提取有价值的新知识点。

已知行业关键词（不需要重复）: {known_keywords}

请从对话中提取：
1. 用户提到的行业关键词（不在上面的已知列表中的）
2. 用户提到的具体变现方式（如果wiki中没有的）
3. 用户的实际定价信息
4. 用户提到的获客渠道
5. 用户提到的交付方式

严格输出JSON，格式：
{{
  "new_keywords": ["关键词1", "关键词2"],
  "new_monetization_methods": ["方式1"],
  "actual_pricing": {{"min": 数字, "max": 数字, "note": "说明"}},
  "acquisition_channels": ["渠道1"],
  "delivery_methods": ["方式1"],
  "industry": "用户实际所属行业",
  "user_concerns": ["用户犹豫或担心的问题"]
}}

如果没有发现新的内容，返回空列表。不要编造数据。"""


class InsightEntry(BaseModel):
    timestamp: str
    user_id_hash: str
    industry: str = ""
    new_keywords: list[str] = Field(default_factory=list)
    new_monetization_methods: list[str] = Field(default_factory=list)
    actual_pricing: dict[str, Any] = Field(default_factory=dict)
    acquisition_channels: list[str] = Field(default_factory=list)
    delivery_methods: list[str] = Field(default_factory=list)
    user_concerns: list[str] = Field(default_factory=list)
    product_name: str = ""
    msg_count: int = 0
    force_completed: bool = False


def _known_keywords_text() -> str:
    keywords = sorted(set(HINTS.keys()) | set(HINTS.values()))
    return "、".join(keywords)


async def extract_insights(
    llm: LLMClient,
    conversation_messages: list[dict[str, str]],
    stage_data: dict,
    *,
    force_completed: bool = False,
) -> InsightEntry | None:
    """Call LLM to extract insights from a completed conversation."""
    if not conversation_messages:
        return None

    known = _known_keywords_text()
    system = EXTRACT_INSIGHT_PROMPT.format(known_keywords=known)

    recent_messages = conversation_messages[-10:]
    messages_payload = [{"role": m["role"], "content": m["content"]} for m in recent_messages]

    try:
        result = await llm.chat(
            messages=messages_payload,
            system=system,
            temperature=0.2,
            max_tokens=512,
        )
        parsed = _parse_json_safe(result)
        if parsed is None:
            logger.warning("Insight extraction returned non-JSON")
            return None

        kps = stage_data.get("knowledge_points", [])
        pkg = stage_data.get("product_package", {})
        industry = parsed.pop("industry", "") or (kps[0].get("industry", "") if kps else "")

        entry = InsightEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id_hash=stage_data.get("user_id_hash", ""),
            industry=industry,
            new_keywords=parsed.get("new_keywords", []),
            new_monetization_methods=parsed.get("new_monetization_methods", []),
            actual_pricing=parsed.get("actual_pricing", {}),
            acquisition_channels=parsed.get("acquisition_channels", []),
            delivery_methods=parsed.get("delivery_methods", []),
            user_concerns=parsed.get("user_concerns", []),
            product_name=pkg.get("product_name", ""),
            msg_count=stage_data.get("user_message_count", 0),
            force_completed=force_completed,
        )
        return entry

    except Exception:
        logger.warning("Insight extraction failed", exc_info=True)
        return None


def log_insight(entry: InsightEntry) -> Path:
    """Append an insight entry to the monthly JSONL file."""
    _INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y%m")
    log_file = _INSIGHTS_DIR / f"insights_{month}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json(exclude_none=True) + "\n")
    return log_file


def get_pending_hints(min_occurrences: int = 2) -> dict[str, int]:
    """Aggregate new keywords that appeared multiple times, ready for HINTS review.

    Returns keyword → count for keywords not already in HINTS,
    filtered to those appearing >= min_occurrences across all insight files.
    """
    keyword_counts: dict[str, int] = {}

    for log_file in sorted(_INSIGHTS_DIR.glob("insights_*.jsonl")):
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for kw in entry.get("new_keywords", []):
                    kw = kw.strip()
                    if kw and kw not in HINTS:
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    return {kw: count for kw, count in keyword_counts.items() if count >= min_occurrences}


def _parse_json_safe(text: str) -> dict | None:
    """Best-effort JSON extraction from LLM text."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
