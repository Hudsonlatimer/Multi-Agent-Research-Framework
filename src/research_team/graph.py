"""LangGraph pipeline: plan, research, critique, write, then check citations."""

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from research_team.agents.critic import critique_research
from research_team.agents.planner import plan_topic
from research_team.agents.researcher import collect_sources
from research_team.agents.writer import write_report
from research_team.errors import ResearchError
from research_team.llm import (
    ROLES,
    ChatHandle,
    get_chat_model,
    max_revisions_from_env,
    resolve_provider,
)
from research_team.report import render_markdown, validate_citations
from research_team.state import Report, ResearchState, Source
from research_team.status import emit
from research_team.tools.cache import DiskCache
from research_team.tools.gather import SearchService


def route_after_critic(state: ResearchState) -> str:
    critique = state.get("critique") or {}
    verdict = str(critique.get("verdict", "pass")).lower()
    revision = int(state.get("revision") or 0)
    max_revisions = int(state.get("max_revisions") or 0)
    if verdict == "revise" and revision < max_revisions:
        return "researcher"
    return "writer"


def route_after_citation(state: ResearchState) -> str:
    errors = state.get("citation_errors") or []
    attempts = int(state.get("write_attempts") or 0)
    if errors and attempts < 2:
        return "writer"
    return END


def build_graph(handles: dict[str, ChatHandle], search: SearchService):
    graph = StateGraph(ResearchState)

    def planner_node(state: ResearchState) -> dict:
        plan = plan_topic(handles["planner"], state["topic"])
        return {"plan": plan.model_dump()}

    def researcher_node(state: ResearchState) -> dict:
        return collect_sources(handles["researcher"], state, search)

    def critic_node(state: ResearchState) -> dict:
        critique = critique_research(handles["critic"], state)
        return {"critique": critique.model_dump()}

    def writer_node(state: ResearchState) -> dict:
        report = write_report(handles["writer"], state)
        return {
            "report": report.model_dump(),
            "write_attempts": int(state.get("write_attempts") or 0) + 1,
        }

    def citation_node(state: ResearchState) -> dict:
        report = Report.model_validate(state["report"])
        sources = [Source.model_validate(item) for item in state.get("sources") or []]
        errors = validate_citations(report, sources)
        if errors:
            noun = "citation" if len(errors) == 1 else "citations"
            emit(f"Rejected {len(errors)} unknown {noun}.")
        else:
            emit("Citations match retrieved sources.")
        return {"citation_errors": errors}

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)
    graph.add_node("citation_check", citation_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"researcher": "researcher", "writer": "writer"},
    )
    graph.add_edge("writer", "citation_check")
    graph.add_conditional_edges(
        "citation_check",
        route_after_citation,
        {"writer": "writer", END: END},
    )
    return graph.compile()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "report"


def default_output_path(topic: str) -> Path:
    return Path("reports") / f"{slugify(topic)}.md"


@dataclass
class RunResult:
    markdown_path: Path
    json_path: Path
    report: Report
    citation_errors: list[str]


def _write_outputs(
    markdown_path: Path,
    markdown: str,
    payload: dict,
) -> Path:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path = markdown_path.with_suffix(".json")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return json_path


def run_research(
    topic: str,
    *,
    provider: str | None = None,
    max_revisions: int | None = None,
    out: Path | None = None,
    search: SearchService | None = None,
    handles: dict[str, ChatHandle] | None = None,
) -> RunResult:
    load_dotenv()
    if provider == "demo":
        if handles is None or search is None:
            raise ResearchError("demo", "invalid_input", "The demo runtime was not configured.")
        provider_name = "demo"
    else:
        provider_name = resolve_provider(provider)
    if not topic or not topic.strip():
        raise ResearchError(provider_name, "invalid_input", "Topic is empty.")
    revisions = max_revisions_from_env() if max_revisions is None else max(0, max_revisions)
    if handles is None:
        handles = {role: get_chat_model(provider_name, role=role) for role in ROLES}
    if search is None:
        cache_root = Path(".cache") / "research-team" / uuid.uuid4().hex
        search = SearchService(cache=DiskCache(cache_root))
    app = build_graph(handles, search)
    final_state = app.invoke(
        {
            "topic": topic,
            "provider": provider_name,
            "model": handles["writer"].model,
            "max_revisions": revisions,
            "revision": 0,
            "write_attempts": 0,
            "sources": [],
            "claims": [],
            "citation_errors": [],
        },
        {"recursion_limit": 30},
    )
    report = Report.model_validate(final_state["report"])
    sources = [Source.model_validate(item) for item in final_state.get("sources") or []]
    errors = list(final_state.get("citation_errors") or [])
    markdown_path = Path(out) if out else default_output_path(topic)
    payload = {
        "topic": topic,
        "provider": provider_name,
        "models": {role: handle.model for role, handle in handles.items()},
        "plan": final_state.get("plan"),
        "sources": [source.model_dump() for source in sources],
        "claims": final_state.get("claims") or [],
        "critique": final_state.get("critique"),
        "report": report.model_dump(),
        "citation_errors": errors,
        "revision": final_state.get("revision", 0),
        "write_attempts": final_state.get("write_attempts", 0),
    }
    markdown = render_markdown(report, sources)
    json_path = _write_outputs(markdown_path, markdown, payload)
    if errors:
        preview = "; ".join(errors[:5])
        raise ResearchError(
            provider_name,
            "citation_check",
            f"citation check failed ({len(errors)} problem(s)). Draft written to {markdown_path}. {preview}",
        )
    return RunResult(
        markdown_path=markdown_path,
        json_path=json_path,
        report=report,
        citation_errors=errors,
    )
