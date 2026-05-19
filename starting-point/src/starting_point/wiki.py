"""Read wiki/ directory knowledge pages for prompt injection."""
from __future__ import annotations

import json
import re
from pathlib import Path

_WIKI_ROOT = Path(__file__).resolve().parent / "wiki" / "industries"

HINTS: dict[str, str] = {
    "家装": "建材",
    "涂料": "建材",
    "油漆": "建材",
    "瓷砖": "建材",
    "墙面": "建材",
    "地板": "建材",
    "水电": "建材",
    "装修": "建材",
    "面点": "餐饮",
    "包子": "餐饮",
    "早餐": "餐饮",
    "厨师": "餐饮",
    "饭店": "餐饮",
    "后厨": "餐饮",
    "食材": "餐饮",
    "厨师长": "餐饮",
    "配方": "餐饮",
    "菜谱": "餐饮",
    "炒菜": "餐饮",
    "烧烤": "餐饮",
    "火锅": "餐饮",
    "月嫂": "家政",
    "保洁": "家政",
    "育婴": "家政",
    "收纳": "家政",
    "保姆": "家政",
    "短视频": "内容变现实战案例",
    "内容创作": "内容变现实战案例",
    "抖音": "内容变现实战案例",
    "自媒体": "内容变现实战案例",
    "卤水": "餐饮",
    "酱料": "餐饮",
    "红烧": "餐饮",
    "炖菜": "餐饮",
}


def read_industry_page(industry: str) -> str:
    """Exact match by industry name. Returns empty string on miss."""
    path = (_WIKI_ROOT / f"{industry}.md").resolve()
    if not path.is_relative_to(_WIKI_ROOT):
        return ""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def read_industry_page_fuzzy(industry: str) -> str:
    """Try fuzzy match via industry hints."""
    mapped = HINTS.get(industry)
    if mapped:
        return read_industry_page(mapped)
    return ""


def read_general_page() -> str:
    """Fallback: the universal monetization methodology page."""
    return read_industry_page("通用变现方法论")


def get_wiki_content(industry: str, max_chars: int = 1500) -> str:
    """Three-tier lookup: exact → fuzzy → general. Truncates at paragraph boundary."""
    content = (
        read_industry_page(industry)
        or read_industry_page_fuzzy(industry)
        or read_general_page()
    )
    if len(content) > max_chars:
        cut = content[:max_chars]
        last_para = cut.rfind("\n\n")
        if last_para > max_chars // 2:
            content = cut[:last_para]
        else:
            content = cut.rsplit("\n", 1)[0]
    return content


def parse_wiki_sections(industry: str) -> dict[str, str]:
    """Parse a wiki page into named sections by ## headings.

    Returns a dict mapping section heading (without leading #) to content.
    Falls back through exact → fuzzy → general.
    """
    raw = (
        read_industry_page(industry)
        or read_industry_page_fuzzy(industry)
        or read_general_page()
    )
    if not raw:
        return {}
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("## "):
            if current_heading:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def _resolve_section_key(available: dict[str, str], name: str) -> str:
    """Match a section name against available keys.

    Tries exact match first, then prefix match (e.g. "变现路径" matches
    "变现路径（按起步难度排序）").
    """
    if name in available:
        return name
    for key in available:
        if key.startswith(name) or name.startswith(key):
            return key
    return ""


def get_wiki_sections(industry: str, section_names: list[str] | None = None) -> str:
    """Return selected wiki sections joined with headers.

    If section_names is None, returns all sections (full page).
    Missing sections are silently skipped. Section names support prefix
    matching (e.g. "获客渠道" matches "获客渠道（按行业特点推荐）").
    """
    sections = parse_wiki_sections(industry)
    if not sections:
        return ""
    if section_names is None:
        return "\n\n".join(f"## {k}\n{v}" for k, v in sections.items())
    parts: list[str] = []
    for name in section_names:
        resolved = _resolve_section_key(sections, name)
        if resolved:
            parts.append(f"## {resolved}\n{sections[resolved]}")
    return "\n\n".join(parts)


# --- Insights writeback ---

_INSIGHTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "insights"
_HINTS_FILE = Path(__file__).resolve().parent / "wiki_hints.json"


def _load_insights_entries(months: list[str] | None = None) -> list[dict]:
    """Load insight entries from JSONL files. months=['202605'] for specific months."""
    entries: list[dict] = []
    if not _INSIGHTS_DIR.exists():
        return entries
    files = sorted(_INSIGHTS_DIR.glob("insights_*.jsonl"))
    if months:
        files = [f for f in files if any(m in f.name for m in months)]
    for log_file in files:
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def _industry_from_hints(keyword: str) -> str | None:
    """Resolve a keyword to industry via existing HINTS."""
    return HINTS.get(keyword)


def sync_hints_from_insights(min_occurrences: int = 2, dry_run: bool = False) -> dict[str, list[str]]:
    """Add new keywords from insights to HINTS dict.

    Returns report: {"added": ["kw1->行业"], "skipped": ["kw3 (only 1 occurrence)"]}.
    """
    entries = _load_insights_entries()
    keyword_industry: dict[str, dict[str, int]] = {}

    for entry in entries:
        industry = entry.get("industry", "")
        if not industry:
            continue
        for kw in entry.get("new_keywords", []):
            kw = kw.strip()
            if not kw or kw in HINTS:
                continue
            if kw not in keyword_industry:
                keyword_industry[kw] = {}
            keyword_industry[kw][industry] = keyword_industry[kw].get(industry, 0) + 1

    added: list[str] = []
    skipped: list[str] = []

    for kw, industries in sorted(keyword_industry.items()):
        best_industry = max(industries, key=industries.get)
        total = sum(industries.values())
        if total >= min_occurrences:
            if not dry_run:
                HINTS[kw] = best_industry
            added.append(f"{kw}→{best_industry}({total}次)")
        else:
            skipped.append(f"{kw}({total}次)")

    return {"added": added, "skipped": skipped}


def sync_wiki_pricing_from_insights(
    min_occurrences: int = 2,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """Append verified pricing data from insights to wiki pages.

    Only adds if the industry wiki has a "定价参考" section and the pricing
    combination doesn't already exist there.
    """
    entries = _load_insights_entries()
    pricing_by_industry: dict[str, list[dict]] = {}

    for entry in entries:
        industry = entry.get("industry", "")
        pricing = entry.get("actual_pricing", {})
        if not industry or not pricing:
            continue
        min_val = pricing.get("min")
        max_val = pricing.get("max")
        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
            continue
        pricing_by_industry.setdefault(industry, []).append(pricing)

    updated: list[str] = []
    skipped: list[str] = []

    for industry, pricings in pricing_by_industry.items():
        if len(pricings) < min_occurrences:
            skipped.append(f"{industry}: 仅{len(pricings)}条定价数据")
            continue

        wiki_path = (_WIKI_ROOT / f"{industry}.md").resolve()
        if not wiki_path.is_relative_to(_WIKI_ROOT):
            skipped.append(f"{industry}: invalid path")
            continue
        if not wiki_path.exists():
            skipped.append(f"{industry}: 无wiki页面")
            continue

        content = wiki_path.read_text(encoding="utf-8")
        if "## 定价参考" not in content:
            skipped.append(f"{industry}: 无定价参考段落")
            continue

        avg_min = round(sum(p["min"] for p in pricings) / len(pricings))
        avg_max = round(sum(p["max"] for p in pricings) / len(pricings))
        note = pricings[0].get("note", "")
        # Strip newlines and long content to prevent prompt injection via wiki
        note = note.replace("\n", " ").strip()[:50]

        range_str = f"{avg_min}-{avg_max}元"
        if range_str in content:
            skipped.append(f"{industry}: 定价{range_str}已存在")
            continue

        line = f"\n- **用户验证定价**: {avg_min}-{avg_max}元"
        if note:
            line += f"（{note}）"
        line += f"（基于{len(pricings)}位用户数据）"

        if not dry_run:
            insert_pos = content.find("## 定价参考")
            next_section = content.find("\n## ", insert_pos + 4)
            if next_section == -1:
                content += line
            else:
                content = content[:next_section] + line + content[next_section:]
            wiki_path.write_text(content, encoding="utf-8")

        updated.append(f"{industry}: 添加定价{avg_min}-{avg_max}元({len(pricings)}条)")

    return {"updated": updated, "skipped": skipped}


def sync_all_insights(dry_run: bool = False) -> dict:
    """Run all insight sync operations. Returns combined report."""
    hints_result = sync_hints_from_insights(dry_run=dry_run)
    pricing_result = sync_wiki_pricing_from_insights(dry_run=dry_run)
    return {
        "hints": hints_result,
        "pricing": pricing_result,
        "dry_run": dry_run,
    }
