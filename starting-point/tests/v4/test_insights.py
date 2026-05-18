from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from starting_point.insights import (
    InsightEntry,
    extract_insights,
    get_pending_hints,
    log_insight,
    _parse_json_safe,
)


def test_insight_entry_defaults():
    entry = InsightEntry(
        timestamp="2026-05-18T12:00:00Z",
        user_id_hash="abc12345",
    )
    assert entry.new_keywords == []
    assert entry.new_monetization_methods == []
    assert entry.industry == ""


def test_insight_entry_full():
    entry = InsightEntry(
        timestamp="2026-05-18T12:00:00Z",
        user_id_hash="abc12345",
        industry="窗帘",
        new_keywords=["窗帘", "遮光帘"],
        new_monetization_methods=["上门测量收费"],
        actual_pricing={"min": 99, "max": 299, "note": "按房间收费"},
        acquisition_channels=["闲鱼"],
        delivery_methods=["上门服务"],
        user_concerns=["怕没人买"],
        product_name="窗帘避坑咨询",
        msg_count=6,
    )
    assert entry.industry == "窗帘"
    assert len(entry.new_keywords) == 2


def test_parse_json_safe_valid():
    result = _parse_json_safe('{"new_keywords": ["窗帘"], "industry": "建材"}')
    assert result == {"new_keywords": ["窗帘"], "industry": "建材"}


def test_parse_json_safe_with_markdown():
    text = '```json\n{"new_keywords": ["窗帘"]}\n```'
    result = _parse_json_safe(text)
    assert result == {"new_keywords": ["窗帘"]}


def test_parse_json_safe_with_surrounding_text():
    text = '好的，提取结果如下：\n{"new_keywords": ["窗帘"]}\n以上是结果。'
    result = _parse_json_safe(text)
    assert result == {"new_keywords": ["窗帘"]}


def test_parse_json_safe_invalid():
    assert _parse_json_safe("not json at all") is None
    assert _parse_json_safe("") is None
    assert _parse_json_safe("```no braces```") is None


def test_log_insight_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr("starting_point.insights._INSIGHTS_DIR", tmp_path)

    entry = InsightEntry(
        timestamp="2026-05-18T12:00:00Z",
        user_id_hash="abc12345",
        industry="建材",
        new_keywords=["窗帘"],
    )
    log_file = log_insight(entry)

    assert log_file.exists()
    assert "insights_202605" in log_file.name

    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["industry"] == "建材"
    assert parsed["new_keywords"] == ["窗帘"]


def test_log_insight_appends(tmp_path, monkeypatch):
    monkeypatch.setattr("starting_point.insights._INSIGHTS_DIR", tmp_path)

    entry1 = InsightEntry(timestamp="2026-05-18T12:00:00Z", user_id_hash="a1", industry="建材")
    entry2 = InsightEntry(timestamp="2026-05-18T12:01:00Z", user_id_hash="b2", industry="餐饮")

    log_insight(entry1)
    log_insight(entry2)

    log_file = tmp_path / "insights_202605.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_get_pending_hints_filters_known(tmp_path, monkeypatch):
    monkeypatch.setattr("starting_point.insights._INSIGHTS_DIR", tmp_path)

    entry1 = InsightEntry(
        timestamp="2026-05-18T12:00:00Z",
        user_id_hash="a1",
        new_keywords=["瓷砖", "窗帘", "水管"],
    )
    entry2 = InsightEntry(
        timestamp="2026-05-18T12:01:00Z",
        user_id_hash="b2",
        new_keywords=["窗帘", "花艺"],
    )

    log_insight(entry1)
    log_insight(entry2)

    pending = get_pending_hints(min_occurrences=2)

    # "瓷砖" is in HINTS, "窗帘" appears twice, "水管" once, "花艺" once
    assert "窗帘" in pending
    assert pending["窗帘"] == 2
    assert "瓷砖" not in pending  # already in HINTS
    assert "水管" not in pending  # only 1 occurrence


def test_get_pending_hints_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("starting_point.insights._INSIGHTS_DIR", tmp_path)
    result = get_pending_hints()
    assert result == {}


@pytest.mark.asyncio
async def test_extract_insights_returns_entry():
    llm = AsyncMock()
    llm.chat.return_value = json.dumps({
        "new_keywords": ["窗帘", "遮光帘"],
        "new_monetization_methods": ["上门测量"],
        "actual_pricing": {"min": 99, "max": 299, "note": "按房间"},
        "acquisition_channels": ["闲鱼"],
        "delivery_methods": ["上门"],
        "industry": "窗帘定制",
        "user_concerns": ["怕没人买"],
    })

    messages = [
        {"role": "user", "content": "我做窗帘定制的"},
        {"role": "assistant", "content": "你做几年了？"},
        {"role": "user", "content": "8年，主要做遮光帘和纱帘"},
    ]
    stage_data = {"knowledge_points": [], "product_package": {}}

    entry = await extract_insights(llm, messages, stage_data)

    assert entry is not None
    assert entry.industry == "窗帘定制"
    assert "窗帘" in entry.new_keywords
    assert "遮光帘" in entry.new_keywords


@pytest.mark.asyncio
async def test_extract_insights_empty_messages():
    llm = AsyncMock()
    entry = await extract_insights(llm, [], {})
    assert entry is None


@pytest.mark.asyncio
async def test_extract_insights_handles_bad_json():
    llm = AsyncMock()
    llm.chat.return_value = "I cannot extract insights from this conversation."

    messages = [{"role": "user", "content": "hi"}]
    entry = await extract_insights(llm, messages, {})
    assert entry is None
