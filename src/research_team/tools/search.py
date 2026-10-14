"""DuckDuckGo text search."""

from typing import Any

from research_team.tools.cache import DiskCache


def normalize_web_row(row: dict[str, Any]) -> dict[str, str] | None:
    url = str(row.get("href") or row.get("url") or "").strip()
    if not url:
        return None
    title = str(row.get("title") or url).strip()
    snippet = str(row.get("body") or row.get("snippet") or "").strip()
    return {"title": title, "url": url, "snippet": snippet}


def search_web(query: str, limit: int = 3, cache: DiskCache | None = None) -> list[dict[str, str]]:
    cached = cache.get("web", f"{limit}:{query}") if cache else None
    if cached is not None:
        return list(cached)[:limit]
    try:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException

        raw = DDGS().text(query, max_results=limit)
    except (DDGSException, OSError, TimeoutError):
        return []
    rows = []
    for item in list(raw or []):
        if not isinstance(item, dict):
            continue
        normalized = normalize_web_row(item)
        if normalized:
            rows.append(normalized)
    if cache:
        cache.set("web", f"{limit}:{query}", rows)
    return rows[:limit]
