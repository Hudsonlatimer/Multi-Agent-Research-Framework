"""Decide whether the gathered claims cover the plan."""

from research_team.llm import ChatHandle, invoke_structured
from research_team.state import Claim, Critique, ResearchPlan, Source, format_claims, format_sources
from research_team.status import emit

CRITIC_SYSTEM = (
    "You review research coverage before a report is written. "
    "Pass only if the claims address every planned section with at least one cited fact "
    "and each claim stays within the source excerpts. "
    "Otherwise return revise, name the missing sections, and give up to 3 new search queries. "
    "Do not write the report."
)


def critique_research(handle: ChatHandle, state: dict) -> Critique:
    emit("Reviewing coverage.")
    plan = ResearchPlan.model_validate(state["plan"])
    sources = [Source.model_validate(item) for item in state.get("sources") or []]
    claims = [Claim.model_validate(item) for item in state.get("claims") or []]
    sections = "\n".join(f"- {section}" for section in plan.sections)
    human = (
        f"Topic: {state['topic']}\n\n"
        f"Planned sections:\n{sections}\n\n"
        f"Claims:\n{format_claims(claims)}\n\n"
        f"Sources:\n{format_sources(sources, excerpt_chars=400)}"
    )
    critique = invoke_structured(handle, Critique, CRITIC_SYSTEM, human)
    queries = [query.strip() for query in critique.search_queries if query and query.strip()][:3]
    missing = [
        section.strip() for section in critique.missing_sections if section and section.strip()
    ]
    if critique.verdict == "revise" and not queries:
        topic = state["topic"]
        queries = [f"{topic} {section}" for section in missing][:3]
    return Critique(
        verdict=critique.verdict,
        missing_sections=missing,
        search_queries=queries,
        notes=critique.notes.strip(),
    )
