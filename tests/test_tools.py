import httpx

from research_team.tools.arxiv import parse_arxiv_feed, search_arxiv
from research_team.tools.cache import DiskCache
from research_team.tools.fetch import fetch_excerpt
from research_team.tools.search import normalize_web_row, search_web

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/1234.5678</id>
    <title>Hash  Maps</title>
    <summary>A hash map stores keys.</summary>
  </entry>
</feed>
"""


def test_cache_round_trip(tmp_path):
    cache = DiskCache(tmp_path)
    assert cache.get("web", "hash map") is None
    cache.set("web", "hash map", [{"url": "https://example.com"}])
    assert cache.get("web", "hash map") == [{"url": "https://example.com"}]


def test_normalize_web_row_accepts_href_or_url():
    assert (
        normalize_web_row({"title": "T", "href": "https://example.com", "body": "snippet"})["url"]
        == "https://example.com"
    )
    assert (
        normalize_web_row({"title": "T", "url": "https://example.com/b", "snippet": "s"})["snippet"]
        == "s"
    )
    assert normalize_web_row({"title": "T"}) is None


def test_search_web_uses_the_cache(monkeypatch, tmp_path):
    calls = {"count": 0}

    class FakeDDGS:
        def text(self, query, max_results=3):
            calls["count"] += 1
            return [{"title": "T", "href": "https://example.com", "body": "snippet"}]

    monkeypatch.setattr("ddgs.DDGS", FakeDDGS)
    cache = DiskCache(tmp_path)
    first = search_web("hash map", limit=3, cache=cache)
    second = search_web("hash map", limit=3, cache=cache)
    assert first == [{"title": "T", "url": "https://example.com", "snippet": "snippet"}]
    assert second == first
    assert calls["count"] == 1


def test_parse_arxiv_feed():
    hits = parse_arxiv_feed(ATOM)
    assert hits == [
        {
            "title": "Hash Maps",
            "url": "https://arxiv.org/abs/1234.5678",
            "snippet": "A hash map stores keys.",
        }
    ]


def test_search_arxiv_parses_the_response(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "export.arxiv.org" in str(request.url)
        return httpx.Response(200, text=ATOM)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    cache = DiskCache(tmp_path)
    hits = search_arxiv("hash map", limit=2, cache=cache, pause=False, client=client)
    again = search_arxiv("hash map", limit=2, cache=cache, pause=False, client=client)
    assert hits[0]["url"] == "https://arxiv.org/abs/1234.5678"
    assert again == hits


def test_fetch_excerpt_extracts_and_caches(tmp_path):
    html = "<html><body><article><p>A hash map stores keys by hash.</p></article></body></html>"
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, text=html)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    cache = DiskCache(tmp_path)
    text = fetch_excerpt("https://example.com/hash", cache=cache, client=client)
    cached = fetch_excerpt("https://example.com/hash", cache=cache, client=client)
    assert "hash map" in text.lower()
    assert cached == text
    assert calls["count"] == 1
