"""Turn a topic into sections and search queries."""

from research_team.llm import ChatHandle, invoke_structured
from research_team.state import ResearchPlan
from research_team.status import emit

PLANNER_SYSTEM = (
    "You plan a technical research report. Return a title, 3 to 5 section headings, "
    "and 3 to 4 web search queries that would find authoritative sources. "
    "Queries must be specific. Do not write the report."
)


def plan_topic(handle: ChatHandle, topic: str) -> ResearchPlan:
    emit("Planning the report.")
    plan = invoke_structured(handle, ResearchPlan, PLANNER_SYSTEM, f"Topic: {topic}")
    queries = [query.strip() for query in plan.search_queries if query and query.strip()][:4]
    sections = [section.strip() for section in plan.sections if section and section.strip()][:5]
    title = (plan.title or "").strip() or topic
    return ResearchPlan(
        title=title,
        sections=sections or ["Overview"],
        search_queries=queries or [topic],
    )
