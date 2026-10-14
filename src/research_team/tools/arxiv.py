"""arXiv API search for technical topics."""

import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import httpx

from research_team.tools.cache import DiskCache
from research_team.tools.http import USER_AGENT

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "https://export.arxiv.org/api/query"
_last_arxiv_at = 0.0


def _wait_for_arxiv() -> None:
    """arXiv asks for at least three seconds between requests."""
    global _last_arxiv_at
    if _last_arxiv_at:
        remaining = 3.0 - (time.monotonic() - _last_arxiv_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_arxiv_at = time.monotonic()


def parse_arxiv_feed(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    hits = []
    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        url = (entry.findtext(f"{ATOM}id") or "").strip()
        if not title or not url.startswith("http"):
            continue
        hits.append({"title": title, "url": url, "snippet": summary or title})
    return hits


def search_arxiv(
    query: str,
    limit: int = 2,
    cache: DiskCache | None = None,
    pause: bool = True,
    client: httpx.Client | None = None,
) -> list[dict[str, str]]:
    cache_key = f"{limit}:{query}"
    cached = cache.get("arxiv", cache_key) if cache else None
    if cached is not None:
        return list(cached)[:limit]
    safe = query.replace('"', "")
    params = urlencode({"search_query": f'all:"{safe}"', "start": 0, "max_results": limit})
    url = f"{ARXIV_API}?{params}"
    own_client = client is None
    http = client or httpx.Client(
        timeout=30,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
    try:
        if pause:
            _wait_for_arxiv()
        response = http.get(url)
        response.raise_for_status()
        hits = parse_arxiv_feed(response.text)[:limit]
    except (httpx.HTTPError, ET.ParseError, OSError):
        return []
    finally:
        if own_client:
            http.close()
    if cache:
        cache.set("arxiv", cache_key, hits)
    return hits
