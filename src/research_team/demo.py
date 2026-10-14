"""Offline demo. No API key and no network.

The writer cites S99 once. The citation check rejects it, and the second draft
uses only the bundled source.
"""

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
from research_team.tools.gather import Page, SearchService

DEMO_TOPIC = "How a Bloom filter rejects a missing key"
DEMO_URL = "https://en.wikipedia.org/wiki/Bloom_filter"
DEMO_EXCERPT = (
    "A Bloom filter is a space-efficient probabilistic data structure, conceived by "
    "Burton Howard Bloom in 1970, that is used to test whether an element is a member "
    "of a set. False positive matches are possible, but false negatives are not."
)


class DemoSearch(SearchService):
    def gather(self, query: str) -> list[Page]:
        return [
            Page(
                title="Bloom filter",
                url=DEMO_URL,
                excerpt=DEMO_EXCERPT,
            )
        ]


class DemoModel:
    def __init__(self) -> None:
        self.critiques = 0
        self.writes = 0

    def with_structured_output(self, schema):
        parent = self

        class Runnable:
            def invoke(self, messages):
                blob = str(messages)
                if schema is ResearchPlan:
                    return ResearchPlan(
                        title="How a Bloom filter rejects a missing key",
                        sections=["Membership", "False results"],
                        search_queries=["Bloom filter membership test"],
                    )
                if schema is Extraction:
                    return Extraction(
                        claims=[
                            ExtractedClaim(
                                text="A Bloom filter tests whether an element is a member of a set.",
                                source_ids=["S1"],
                            ),
                            ExtractedClaim(
                                text="False positive matches are possible, but false negatives are not.",
                                source_ids=["S1"],
                            ),
                            ExtractedClaim(
                                text="Burton Howard Bloom conceived the structure in 1970.",
                                source_ids=["S1"],
                            ),
                        ]
                    )
                if schema is Critique:
                    parent.critiques += 1
                    if parent.critiques == 1:
                        return Critique(
                            verdict="revise",
                            missing_sections=["False results"],
                            search_queries=["Bloom filter false negatives"],
                        )
                    return Critique(
                        verdict="pass", notes="The membership and false-result claims are sourced."
                    )
                if schema is Report:
                    parent.writes += 1
                    claims = [
                        Claim(
                            text="A Bloom filter tests whether an element is a member of a set.",
                            source_ids=["S1"],
                        ),
                        Claim(
                            text="False positive matches are possible, but false negatives are not.",
                            source_ids=["S1"],
                        ),
                    ]
                    if "citation check" not in blob:
                        return Report(
                            title="How a Bloom filter rejects a missing key",
                            summary="A Bloom filter can prove a key was never inserted. [S99]",
                            sections=[
                                Section(heading="Membership", claims=[claims[0]]),
                                Section(heading="False results", claims=[claims[1]]),
                            ],
                            limitations="The bit-array math is not in the source.",
                        )
                    return Report(
                        title="How a Bloom filter rejects a missing key",
                        summary=(
                            "A Bloom filter tests set membership. It can say a key is definitely "
                            "absent. False positives are possible, but false negatives are not. [S1]"
                        ),
                        sections=[
                            Section(heading="Membership", claims=[claims[0]]),
                            Section(
                                heading="False results",
                                claims=[
                                    claims[1],
                                    Claim(
                                        text="Burton Howard Bloom conceived the structure in 1970.",
                                        source_ids=["S1"],
                                    ),
                                ],
                            ),
                        ],
                        limitations=(
                            "The source does not give the false-positive rate formula or the "
                            "bit-array layout."
                        ),
                    )
                raise AssertionError(schema.__name__)

        return Runnable()


def demo_handles() -> dict[str, ChatHandle]:
    model = DemoModel()
    return {
        role: ChatHandle(provider="demo", model="offline-demo", role=role, client=model)
        for role in ("planner", "researcher", "critic", "writer")
    }


def demo_search() -> DemoSearch:
    return DemoSearch()
