"""Write the report from approved claims only."""

from research_team.llm import ChatHandle, invoke_structured
from research_team.state import Claim, Report, ResearchPlan, Source
from research_team.status import emit

WRITER_SYSTEM = (
    "You write a technical report using only the claims and sources provided. "
    "Every factual statement in a section must be one of the supplied claims and must keep that claim's source ids. "
    "Do not invent sources, numbers, or citations. "
    "Keep the wording of each claim close to its source excerpt. "
    "The summary and limitations may cite only known source ids. "
    "Use limitations to state what the sources do not cover."
)


def write_report(handle: ChatHandle, state: dict) -> Report:
    emit("Writing the report.")
    plan = ResearchPlan.model_validate(state["plan"])
    sources = [Source.model_validate(item) for item in state.get("sources") or []]
    claims = [Claim.model_validate(item) for item in state.get("claims") or []]
    known_ids = ", ".join(source.id for source in sources) or "(none)"
    claim_lines = "\n".join(
        f"- {claim.text} | sources: {', '.join(claim.source_ids)}" for claim in claims
    )
    if not claim_lines:
        claim_lines = "No claims were extracted."
    source_lines = (
        "\n".join(f"[{source.id}] {source.title} — {source.url}" for source in sources)
        or "No sources."
    )
    sections = "\n".join(f"- {section}" for section in plan.sections)
    errors = state.get("citation_errors") or []
    repair = ""
    if errors:
        listed = "\n".join(f"- {error}" for error in errors)
        repair = (
            "\n\nThe previous draft failed the citation check. Fix every problem. "
            f"Use only these source ids: {known_ids}.\n{listed}"
        )
    human = (
        f"Topic: {state['topic']}\n"
        f"Title: {plan.title}\n\n"
        f"Sections to cover:\n{sections}\n\n"
        f"Allowed claims:\n{claim_lines}\n\n"
        f"Allowed sources:\n{source_lines}"
        f"{repair}"
    )
    return invoke_structured(handle, Report, WRITER_SYSTEM, human)
