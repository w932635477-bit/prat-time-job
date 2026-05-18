"""Read wiki/ directory knowledge pages for prompt injection."""
from __future__ import annotations

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
    "月嫂": "家政",
    "保洁": "家政",
    "育婴": "家政",
    "收纳": "家政",
    "保姆": "家政",
    "短视频": "内容变现实战案例",
    "内容创作": "内容变现实战案例",
    "抖音": "内容变现实战案例",
    "自媒体": "内容变现实战案例",
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
