"""Render a report and reject source ids that were never retrieved."""

import re

from research_team.state import Report, Source

SOURCE_MARKER = re.compile(r"\[(S\d+)\]")


def validate_citations(report: Report, sources: list[Source]) -> list[str]:
    known = {source.id for source in sources}
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
            for source_id in claim.source_ids:
                if source_id not in known:
                    errors.append(f"Unknown source id {source_id} on claim: {claim.text}")
    return errors


def cited_source_ids(report: Report, sources: list[Source]) -> list[str]:
    known = {source.id for source in sources}
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
    unknown = len(validate_citations(report, sources))
    return (
        f"> {_counted(cited, 'source')} cited · {_counted(claims, 'claim')} · "
        f"{_counted(unknown, 'unknown citation')}"
    )


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
