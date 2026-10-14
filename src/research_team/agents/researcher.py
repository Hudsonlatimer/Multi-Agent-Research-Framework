"""Search planned queries and extract claims that cite source ids."""

from datetime import UTC, datetime

from research_team.llm import ChatHandle, invoke_structured
from research_team.report import claim_supported
from research_team.state import (
    Claim,
    Critique,
    Extraction,
    ResearchPlan,
    Source,
    format_sources,
    normalize_source_id,
)
from research_team.status import emit
from research_team.tools.gather import Page, SearchService

RESEARCHER_SYSTEM = (
    "You extract factual claims from source excerpts for a technical report. "
    "Every claim must be supported by the excerpt text. Cite only the source ids you were given. "
    "Do not use outside knowledge. Skip claims you cannot support."
)

MAX_PLAN_QUERIES = 4
MAX_REVISION_QUERIES = 3


def _dropped_label(count: int) -> str:
    noun = "claim" if count == 1 else "claims"
    return f"{count} ungrounded {noun}"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def queries_for_state(
    plan: ResearchPlan, critique: Critique | None, revision: int
) -> tuple[list[str], int]:
    if critique and critique.verdict == "revise":
        queries = [query.strip() for query in critique.search_queries if query and query.strip()]
        if not queries:
            queries = [section for section in critique.missing_sections if section.strip()]
        return queries[:MAX_REVISION_QUERIES], revision + 1
    queries = [query.strip() for query in plan.search_queries if query and query.strip()]
    return queries[:MAX_PLAN_QUERIES] or [plan.title], revision


def assign_sources(
    pages: list[Page], existing: list[Source], new_sources: list[Source]
) -> list[Source]:
    known = {source.url: source for source in existing + new_sources}
    batch: list[Source] = []
    for page in pages:
        found = known.get(page.url)
        if found:
            batch.append(found)
            continue
        source = Source(
            id=f"S{len(existing) + len(new_sources) + 1}",
            title=page.title.strip() or page.url,
            url=page.url,
            retrieved_at=utc_now(),
            excerpt=page.excerpt.strip(),
        )
        known[page.url] = source
        new_sources.append(source)
        batch.append(source)
    return batch


def claims_from_extraction(
    extraction: Extraction, allowed: dict[str, Source]
) -> tuple[list[Claim], int]:
    claims: list[Claim] = []
    dropped = 0
    for extracted in extraction.claims:
        text = extracted.text.strip()
        ids: list[str] = []
        for source_id in extracted.source_ids:
            normalized = normalize_source_id(source_id)
            if normalized in allowed and normalized not in ids:
                ids.append(normalized)
        if not text or not ids:
            continue
        excerpts = [allowed[source_id].excerpt for source_id in ids]
        if not claim_supported(text, excerpts):
            dropped += 1
            continue
        claims.append(Claim(text=text, source_ids=ids))
    return claims, dropped


def collect_sources(handle: ChatHandle, state: dict, search: SearchService) -> dict:
    plan = ResearchPlan.model_validate(state["plan"])
    critique = Critique.model_validate(state["critique"]) if state.get("critique") else None
    revision = int(state.get("revision") or 0)
    queries, revision = queries_for_state(plan, critique, revision)
    existing = [Source.model_validate(item) for item in state.get("sources") or []]
    new_sources: list[Source] = []
    new_claims: list[Claim] = []
    for query in queries:
        emit(f"Searching: {query}")
        pages = search.gather(query)
        batch = assign_sources(pages, existing, new_sources)
        if not batch:
            continue
        allowed = {source.id: source for source in batch}
        extraction = invoke_structured(
            handle,
            Extraction,
            RESEARCHER_SYSTEM,
            f"Topic: {state['topic']}\nSearch query: {query}\n\nSources:\n{format_sources(batch)}",
        )
        grounded, dropped = claims_from_extraction(extraction, allowed)
        if dropped:
            emit(f"Dropped {_dropped_label(dropped)}.")
        new_claims.extend(grounded)
    return {
        "revision": revision,
        "sources": [source.model_dump() for source in new_sources],
        "claims": [claim.model_dump() for claim in new_claims],
    }
