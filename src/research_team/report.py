"""Render a report and reject source ids that were never retrieved."""

import re

from research_team.state import Report, Source

SOURCE_MARKER = re.compile(r"\[(S\d+)\]")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "have",
        "been",
        "were",
        "their",
        "about",
        "which",
        "would",
        "could",
        "should",
        "into",
        "than",
        "then",
        "also",
        "only",
        "after",
        "before",
        "where",
        "when",
        "what",
        "your",
        "they",
        "them",
        "some",
        "such",
        "other",
        "more",
        "most",
        "each",
        "both",
        "does",
    }
)


def distinctive_words(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if len(word) > 3 and word not in _STOP}


def claim_supported(text: str, excerpts: list[str]) -> bool:
    """A claim is supported when most of its distinctive words appear in the excerpts."""
    words = distinctive_words(text)
    if len(words) < 2:
        return False
    overlap = words & distinctive_words(" ".join(excerpts))
    return len(overlap) >= 2 and len(overlap) * 2 >= len(words)


def supporting_quote(text: str, excerpts: list[str]) -> str | None:
    """Return a sentence copied from the excerpts, not a sentence written by the model."""
    words = distinctive_words(text)
    best = ""
    best_score = 0
    for excerpt in excerpts:
        for sentence in _sentences(excerpt):
            overlap = len(words & distinctive_words(sentence))
            if overlap > best_score:
                best_score = overlap
                best = sentence
    if best_score < 2:
        return None
    return best


def _sentences(excerpt: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", " ".join(excerpt.split()))
    return [part.strip() for part in parts if part.strip()]


def validate_citations(report: Report, sources: list[Source]) -> list[str]:
    known = {source.id: source for source in sources}
    errors: list[str] = []
    for label, text in (("summary", report.summary), ("limitations", report.limitations)):
        for source_id in SOURCE_MARKER.findall(text):
            if source_id not in known:
                errors.append(f"Unknown source id {source_id} in {label}.")
    for section in report.sections:
        for claim in section.claims:
            if not claim.source_ids:
                errors.append(f"Claim has no sources: {claim.text}")
                continue
            missing = [source_id for source_id in claim.source_ids if source_id not in known]
            for source_id in missing:
                errors.append(f"Unknown source id {source_id} on claim: {claim.text}")
            if missing:
                continue
            excerpts = [known[source_id].excerpt for source_id in claim.source_ids]
            if not claim_supported(claim.text, excerpts):
                errors.append(f"Claim is not supported by its sources: {claim.text}")
    return errors


def cited_source_ids(report: Report, sources: list[Source]) -> list[str]:
    known = set(source.id for source in sources)
    ordered: list[str] = []

    def add(source_id: str) -> None:
        if source_id in known and source_id not in ordered:
            ordered.append(source_id)

    for source_id in SOURCE_MARKER.findall(report.summary):
        add(source_id)
    for section in report.sections:
        for claim in section.claims:
            for source_id in claim.source_ids:
                add(source_id)
    for source_id in SOURCE_MARKER.findall(report.limitations):
        add(source_id)
    return ordered


def _counted(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def integrity_line(report: Report, sources: list[Source]) -> str:
    claims = sum(len(section.claims) for section in report.sections)
    cited = len(cited_source_ids(report, sources))
    quotes = _quote_count(report, sources)
    unknown = len(validate_citations(report, sources))
    return (
        f"> {_counted(cited, 'source')} cited · {_counted(claims, 'claim')} · "
        f"{_counted(quotes, 'quote')} · {_counted(unknown, 'unknown citation')}"
    )


def _quote_count(report: Report, sources: list[Source]) -> int:
    by_id = {source.id: source for source in sources}
    count = 0
    for section in report.sections:
        for claim in section.claims:
            excerpts = [
                by_id[source_id].excerpt for source_id in claim.source_ids if source_id in by_id
            ]
            if supporting_quote(claim.text, excerpts):
                count += 1
    return count


def render_markdown(report: Report, sources: list[Source]) -> str:
    by_id = {source.id: source for source in sources}
    lines = [
        f"# {report.title}",
        "",
        integrity_line(report, sources),
        "",
        report.summary.strip(),
        "",
    ]
    for section in report.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        for claim in section.claims:
            markers = "".join(f"[{source_id}]" for source_id in claim.source_ids)
            suffix = f" {markers}" if markers else ""
            lines.append(f"- {claim.text.strip()}{suffix}")
            excerpts = [
                by_id[source_id].excerpt for source_id in claim.source_ids if source_id in by_id
            ]
            quote = supporting_quote(claim.text, excerpts)
            if quote:
                lines.append(f"  > {quote}")
        lines.append("")
    lines.extend(["## Limitations", "", report.limitations.strip(), "", "## Bibliography", ""])
    cited = cited_source_ids(report, sources)
    if not cited:
        lines.append("No sources were cited.")
    else:
        for source_id in cited:
            source = by_id[source_id]
            lines.append(
                f"- [{source_id}] {source.title}. {source.url} (retrieved {source.retrieved_at})"
            )
    lines.append("")
    return "\n".join(lines)
