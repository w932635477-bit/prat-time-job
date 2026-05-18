from __future__ import annotations

import pytest

from starting_point.wiki import parse_wiki_sections, get_wiki_sections, get_wiki_content


class TestParseWikiSections:
    def test_parses_known_industry(self):
        sections = parse_wiki_sections("建材")
        assert isinstance(sections, dict)
        assert len(sections) > 0
        # Section names include parenthetical suffixes
        has_path = any("变现路径" in k for k in sections)
        has_pricing = any("定价参考" in k for k in sections)
        has_channel = any("获客渠道" in k for k in sections)
        assert has_path, f"No '变现路径' section, keys: {list(sections.keys())}"
        assert has_pricing, f"No '定价参考' section, keys: {list(sections.keys())}"
        assert has_channel, f"No '获客渠道' section, keys: {list(sections.keys())}"

    def test_fuzzy_match_via_hints(self):
        sections = parse_wiki_sections("瓷砖")
        assert len(sections) > 0
        has_path = any("变现路径" in k for k in sections)
        assert has_path

    def test_fallback_to_general(self):
        sections = parse_wiki_sections("不存在的行业xyz")
        assert len(sections) > 0

    def test_section_content_not_empty(self):
        sections = parse_wiki_sections("建材")
        for name, content in sections.items():
            assert len(content) > 0, f"Section '{name}' is empty"

    def test_heading_not_in_content(self):
        sections = parse_wiki_sections("建材")
        for name, content in sections.items():
            assert not content.startswith("## "), f"Section '{name}' starts with ##"


class TestGetWikiSections:
    def test_returns_selected_sections_with_prefix_match(self):
        result = get_wiki_sections("建材", ["定价参考", "获客渠道"])
        assert "## 定价参考" in result
        assert "## 获客渠道" in result
        assert "## 变现路径" not in result

    def test_skips_missing_sections(self):
        result = get_wiki_sections("建材", ["定价参考", "不存在的段落"])
        assert "## 定价参考" in result
        assert "不存在的段落" not in result

    def test_returns_all_when_none_specified(self):
        result = get_wiki_sections("建材")
        assert "变现路径" in result
        assert "定价参考" in result

    def test_fallback_general_page_has_different_sections(self):
        # Unknown industry falls back to general page with different section names
        result = get_wiki_sections("完全不存在的行业abc", ["定价"])
        # General page has "定价方法（通用公式）" — prefix match should find it
        assert "定价" in result

    def test_single_section(self):
        result = get_wiki_sections("餐饮", ["用户常见顾虑"])
        assert "## 用户常见顾虑" in result
        assert "## 获客渠道" not in result


class TestGetWikiContentBackwardsCompat:
    def test_still_returns_content(self):
        content = get_wiki_content("建材")
        assert len(content) > 0
        assert "装修" in content or "建材" in content

    def test_respects_max_chars(self):
        content = get_wiki_content("建材", max_chars=500)
        assert len(content) <= 500
