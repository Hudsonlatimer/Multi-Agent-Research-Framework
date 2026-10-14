"""Bounded search: web + arXiv, then a short excerpt from each page."""

from dataclasses import dataclass

import httpx

from research_team.tools.arxiv import search_arxiv
from research_team.tools.cache import DiskCache
from research_team.tools.fetch import fetch_excerpt
from research_team.tools.http import USER_AGENT
from research_team.tools.search import search_web


@dataclass
class Page:
    title: str
    url: str
    excerpt: str


@dataclass
class SearchService:
    cache: DiskCache | None = None
    web_limit: int = 3
    arxiv_limit: int = 2
    fetch_limit: int = 3
    excerpt_chars: int = 1000
    pause_arxiv: bool = True

    def gather(self, query: str) -> list[Page]:
        hits = search_web(query, limit=self.web_limit, cache=self.cache)
        with httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as http:
            hits.extend(
                search_arxiv(
                    query,
                    limit=self.arxiv_limit,
                    cache=self.cache,
                    pause=self.pause_arxiv,
                    client=http,
                )
            )
            pages: list[Page] = []
            seen: set[str] = set()
            for hit in hits:
                url = hit["url"]
                if url in seen:
                    continue
                seen.add(url)
                excerpt = fetch_excerpt(
                    url,
                    limit=self.excerpt_chars,
                    cache=self.cache,
                    client=http,
                ) or hit.get("snippet", "")
                excerpt = " ".join(excerpt.split())[: self.excerpt_chars]
                if not excerpt:
                    continue
                pages.append(Page(title=hit.get("title") or url, url=url, excerpt=excerpt))
                if len(pages) >= self.fetch_limit:
                    break
        return pages
