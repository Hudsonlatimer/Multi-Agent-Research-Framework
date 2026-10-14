"""Fetch a page and keep the main text."""

import httpx
import trafilatura

from research_team.tools.cache import DiskCache
from research_team.tools.http import USER_AGENT


def fetch_excerpt(
    url: str,
    limit: int = 1000,
    cache: DiskCache | None = None,
    client: httpx.Client | None = None,
) -> str:
    cached = cache.get("fetch", url) if cache else None
    if isinstance(cached, str):
        return cached[:limit]
    own_client = client is None
    http = client or httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    text = ""
    try:
        response = http.get(url)
        response.raise_for_status()
        extracted = (
            trafilatura.extract(response.text, include_comments=False, include_tables=False) or ""
        )
        text = " ".join(extracted.split())
    except Exception:
        text = ""
    finally:
        if own_client:
            http.close()
    if cache:
        cache.set("fetch", url, text)
    return text[:limit]
