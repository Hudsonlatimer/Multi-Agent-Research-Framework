from research_team.errors import ResearchError
from research_team.graph import run_research
from research_team.llm import ChatHandle
from research_team.state import (
    Claim,
    Critique,
    ExtractedClaim,
    Extraction,
    Report,
    ResearchPlan,
    Section,
)
from research_team.status import bind_status, reset_status
from research_team.tools.gather import Page, SearchService


class StaticSearch(SearchService):
    def gather(self, query: str) -> list[Page]:
        return [
            Page(
                title="Hash map notes",
                url="https://example.com/hash",
                excerpt="A hash map stores keys by hash.",
            )
        ]


class ScriptedModel:
    def __init__(self, bad_citation: bool = False) -> None:
        self.critiques = 0
        self.writes = 0
        self.bad_citation = bad_citation

    def with_structured_output(self, schema):
        parent = self

        class Runnable:
            def invoke(self, messages):
                blob = str(messages)
                if schema is ResearchPlan:
                    return ResearchPlan(
                        title="Hash maps",
                        sections=["Definition", "Collisions"],
                        search_queries=["hash map data structure"],
                    )
                if schema is Extraction:
                    return Extraction(
                        claims=[
                            ExtractedClaim(
                                text="A hash map stores keys by hash.", source_ids=["s1"]
                            )
                        ]
                    )
                if schema is Critique:
                    parent.critiques += 1
                    if parent.critiques == 1:
                        return Critique(
                            verdict="revise",
                            missing_sections=["Collisions"],
                            search_queries=["hash map collision resolution"],
                        )
                    return Critique(verdict="pass", notes="Coverage is enough.")
                if schema is Report:
                    parent.writes += 1
                    failed = parent.bad_citation or (
                        "citation check" not in blob and parent.writes == 1
                    )
                    if parent.bad_citation or failed:
                        return Report(
                            title="Hash maps",
                            summary="Overview [S99]",
                            sections=[
                                Section(
                                    heading="Definition",
                                    claims=[
                                        Claim(
                                            text="A hash map stores keys by hash.",
                                            source_ids=["S1"],
                                        )
                                    ],
                                )
                            ],
                            limitations="Sources are limited.",
                        )
                    return Report(
                        title="Hash maps",
                        summary="A hash map stores keys by hash. [S1]",
                        sections=[
                            Section(
                                heading="Definition",
                                claims=[
                                    Claim(text="A hash map stores keys by hash.", source_ids=["S1"])
                                ],
                            )
                        ],
                        limitations="Collision details were not in the source.",
                    )
                raise AssertionError(schema.__name__)

        return Runnable()


def _handles(model) -> dict[str, ChatHandle]:
    return {
        role: ChatHandle(provider="groq", model="fake", role=role, client=model)
        for role in ("planner", "researcher", "critic", "writer")
    }


def test_graph_revises_once_then_fixes_citations(tmp_path, monkeypatch):
    monkeypatch.setattr("research_team.graph.load_dotenv", lambda *args, **kwargs: None)
    model = ScriptedModel()
    messages: list[str] = []
    token = bind_status(messages.append)
    try:
        result = run_research(
            "hash maps",
            provider="groq",
            max_revisions=1,
            out=tmp_path / "hash-maps.md",
            search=StaticSearch(),
            handles=_handles(model),
        )
    finally:
        reset_status(token)
    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert model.critiques == 2
    assert model.writes == 2
    assert result.citation_errors == []
    assert "https://example.com/hash" in markdown
    assert "[S99]" not in markdown
    payload = result.json_path.read_text(encoding="utf-8")
    assert '"revision": 1' in payload
    assert '"write_attempts": 2' in payload
    assert "Planning the report." in messages
    assert messages.count("Writing the report.") == 2
    assert "Rejected 1 unknown citation." in messages
    assert "Citations match retrieved sources." in messages


def test_graph_fails_when_citations_stay_unknown(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr("research_team.graph.load_dotenv", lambda *args, **kwargs: None)
    model = ScriptedModel(bad_citation=True)
    out = tmp_path / "hash-maps.md"
    with pytest.raises(ResearchError) as caught:
        run_research(
            "hash maps",
            provider="groq",
            max_revisions=0,
            out=out,
            search=StaticSearch(),
            handles=_handles(model),
        )
    assert caught.value.kind == "citation_check"
    assert caught.value.provider == "groq"
    assert out.exists()
    assert model.writes == 2
