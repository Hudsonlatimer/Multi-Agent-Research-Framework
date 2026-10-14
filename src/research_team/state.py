"""Shared report contract. Graph state stores these models as plain dicts."""

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    id: str
    title: str
    url: str
    retrieved_at: str
    excerpt: str


class Claim(BaseModel):
    text: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class Section(BaseModel):
    heading: str = Field(min_length=1)
    claims: list[Claim] = Field(default_factory=list)


class Report(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    sections: list[Section] = Field(default_factory=list)
    limitations: str = Field(min_length=1)


class ResearchPlan(BaseModel):
    title: str
    sections: list[str]
    search_queries: list[str]


class Critique(BaseModel):
    verdict: Literal["pass", "revise"]
    missing_sections: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, value: object) -> str:
        text = str(value).strip().lower()
        if text not in {"pass", "revise"}:
            raise ValueError("verdict must be pass or revise")
        return text


class ExtractedClaim(BaseModel):
    text: str = ""
    source_ids: list[str] = Field(default_factory=list)


class Extraction(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


class ResearchState(TypedDict, total=False):
    topic: str
    provider: str
    model: str
    max_revisions: int
    revision: int
    write_attempts: int
    plan: dict
    sources: Annotated[list[dict], operator.add]
    claims: Annotated[list[dict], operator.add]
    critique: dict
    report: dict
    citation_errors: list[str]


def format_sources(sources: list[Source], excerpt_chars: int = 800) -> str:
    if not sources:
        return "No sources were retrieved."
    blocks = []
    for source in sources:
        excerpt = " ".join(source.excerpt.split())[:excerpt_chars]
        blocks.append(f"[{source.id}] {source.title}\nURL: {source.url}\nExcerpt: {excerpt}")
    return "\n\n".join(blocks)


def format_claims(claims: list[Claim]) -> str:
    if not claims:
        return "No claims were extracted."
    lines = []
    for claim in claims:
        ids = ", ".join(claim.source_ids)
        lines.append(f"- {claim.text} [{ids}]")
    return "\n".join(lines)


def normalize_source_id(value: str) -> str:
    text = value.strip().strip("[]").upper()
    return text
