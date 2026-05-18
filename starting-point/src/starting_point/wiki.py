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
