from langgraph.graph import END

from research_team.graph import route_after_citation, route_after_critic


def test_critic_sends_gaps_back_to_the_researcher():
    assert (
        route_after_critic({"critique": {"verdict": "revise"}, "revision": 0, "max_revisions": 1})
        == "researcher"
    )


def test_critic_passes_to_the_writer():
    assert (
        route_after_critic({"critique": {"verdict": "pass"}, "revision": 0, "max_revisions": 1})
        == "writer"
    )


def test_critic_stops_at_the_revision_cap():
    assert (
        route_after_critic({"critique": {"verdict": "revise"}, "revision": 1, "max_revisions": 1})
        == "writer"
    )


def test_zero_revisions_go_straight_to_the_writer():
    assert (
        route_after_critic({"critique": {"verdict": "revise"}, "revision": 0, "max_revisions": 0})
        == "writer"
    )


def test_citation_failure_retries_the_writer_once():
    assert (
        route_after_citation({"citation_errors": ["Unknown source id S99"], "write_attempts": 1})
        == "writer"
    )


def test_second_citation_failure_ends_the_run():
    assert (
        route_after_citation({"citation_errors": ["Unknown source id S99"], "write_attempts": 2})
        == END
    )


def test_clean_citations_end_the_run():
    assert route_after_citation({"citation_errors": [], "write_attempts": 1}) == END
