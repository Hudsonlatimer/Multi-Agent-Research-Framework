from research_team.report import (
    cited_source_ids,
    integrity_line,
    render_markdown,
    validate_citations,
)
from research_team.state import Claim, Report, Section, Source


def _sources() -> list[Source]:
    return [
        Source(
            id="S1",
            title="Hash map notes",
            url="https://example.com/hash",
            retrieved_at="2026-10-13T00:00:00+00:00",
            excerpt="A hash map stores keys.",
        ),
        Source(
            id="S2",
            title="Unused paper",
            url="https://example.com/unused",
            retrieved_at="2026-10-13T00:00:00+00:00",
            excerpt="Not cited.",
        ),
    ]


def _report(**overrides) -> Report:
    data = {
        "title": "Hash maps",
        "summary": "A hash map stores keys by hash. [S1]",
        "sections": [
            Section(
                heading="Definition",
                claims=[Claim(text="A hash map stores keys by hash.", source_ids=["S1"])],
            ),
        ],
        "limitations": "Collision details were not retrieved.",
    }
    data.update(overrides)
    return Report.model_validate(data)


def test_valid_citations_pass():
    assert validate_citations(_report(), _sources()) == []


def test_unknown_claim_source_fails():
    report = _report(
        sections=[
            Section(heading="Definition", claims=[Claim(text="Invented fact.", source_ids=["S99"])])
        ]
    )
    errors = validate_citations(report, _sources())
    assert any("S99" in error for error in errors)


def test_unknown_summary_marker_fails():
    report = _report(summary="A claim with a fake footnote. [S99]")
    errors = validate_citations(report, _sources())
    assert any("summary" in error for error in errors)


def test_bibliography_lists_only_cited_sources():
    markdown = render_markdown(_report(), _sources())
    assert "https://example.com/hash" in markdown
    assert "https://example.com/unused" not in markdown
    assert cited_source_ids(_report(), _sources()) == ["S1"]
    assert "[S1]" in markdown
    assert (
        integrity_line(_report(), _sources()) == "> 1 source cited · 1 claim · 0 unknown citations"
    )
