import pytest

from research_team.agents.planner import plan_topic
from research_team.errors import ResearchError
from research_team.llm import get_chat_model, resolve_provider


@pytest.mark.live
def test_live_planner_returns_queries():
    provider = resolve_provider(None)
    try:
        handle = get_chat_model(provider, role="planner")
    except ResearchError as exc:
        if exc.kind == "missing_key":
            pytest.skip(str(exc))
        raise
    plan = plan_topic(handle, "What is a bloom filter?")
    assert plan.search_queries
    assert plan.sections
