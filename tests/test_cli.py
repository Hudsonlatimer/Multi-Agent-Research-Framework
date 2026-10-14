import pytest

from research_team.cli import run_cli
from research_team.errors import ResearchError
from research_team.graph import RunResult, slugify
from research_team.state import Report


def test_cli_prints_the_report_path(tmp_path, monkeypatch, capsys):
    path = tmp_path / "out.md"
    report = Report(title="T", summary="S", limitations="L")

    def fake_run(topic, **kwargs):
        path.write_text("# T\n", encoding="utf-8")
        return RunResult(path, path.with_suffix(".json"), report, [])

    monkeypatch.setattr("research_team.cli.run_research", fake_run)
    code = run_cli(
        ["hash maps", "--provider", "ollama", "--max-revisions", "0", "--out", str(path)]
    )
    assert code == 0
    assert str(path) in capsys.readouterr().out


def test_cli_names_a_citation_failure(monkeypatch, capsys):
    def fake_run(topic, **kwargs):
        raise ResearchError("groq", "citation_check", "citation check failed (1 problem(s)).")

    monkeypatch.setattr("research_team.cli.run_research", fake_run)
    code = run_cli(["hash maps", "--provider", "groq"])
    captured = capsys.readouterr()
    assert code == 1
    assert "groq: citation_check:" in captured.err


def test_demo_rejects_an_invented_citation_then_writes_the_report(tmp_path, capsys):
    out = tmp_path / "demo.md"
    code = run_cli(["--demo", "--out", str(out)])
    captured = capsys.readouterr()
    assert code == 0
    assert str(out) in captured.out
    assert "Rejected 1 unknown citation." in captured.err
    assert "Citations match retrieved sources." in captured.err
    report = out.read_text(encoding="utf-8")
    assert "https://en.wikipedia.org/wiki/Bloom_filter" in report
    assert "[S99]" not in report
    assert "0 unknown citations" in report


def test_cli_rejects_a_blank_topic(capsys):
    code = run_cli(["   ", "--provider", "ollama"])
    assert code == 1
    assert "ollama: invalid_input:" in capsys.readouterr().err


def test_cli_rejects_negative_revisions():
    with pytest.raises(SystemExit) as caught:
        run_cli(["hash maps", "--max-revisions", "-1"])
    assert caught.value.code == 2


def test_slugify_uses_lowercase_words():
    assert slugify("How RAG cites sources!") == "how-rag-cites-sources"
    assert slugify("???") == "report"


def test_cli_names_a_rate_limit(monkeypatch, capsys):
    def fake_run(topic, **kwargs):
        raise ResearchError("groq", "rate_limit", "groq rate limit reached.")

    monkeypatch.setattr("research_team.cli.run_research", fake_run)
    code = run_cli(["hash maps"])
    assert code == 1
    assert "groq: rate_limit:" in capsys.readouterr().err
