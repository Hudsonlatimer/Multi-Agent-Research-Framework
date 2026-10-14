"""Command line entry: research TOPIC --provider groq --out reports/topic.md"""

import argparse
import sys
from pathlib import Path

from research_team.demo import DEMO_TOPIC, demo_handles, demo_search
from research_team.errors import ResearchError, classify_provider_error
from research_team.graph import run_research
from research_team.llm import resolve_provider
from research_team.status import bind_status, reset_status


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("max revisions cannot be negative")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research",
        description="Write a cited technical report. The run fails if a citation was never fetched.",
    )
    parser.add_argument("topic", nargs="?", help="Topic to research")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the offline Bloom filter demo. No API key and no network.",
    )
    parser.add_argument("--provider", default=None, help="groq, together, gemini, or ollama")
    parser.add_argument("--out", type=Path, default=None, help="Markdown output path")
    parser.add_argument(
        "--max-revisions",
        type=_non_negative_int,
        default=None,
        help="Critic loops before writing (default 1)",
    )
    return parser


def _print_status(message: str) -> None:
    print(message, file=sys.stderr)


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo and args.topic:
        parser.error("--demo does not take a topic")
    if not args.demo and not args.topic:
        parser.error("a topic is required")
    token = bind_status(_print_status)
    try:
        if args.demo:
            result = run_research(
                DEMO_TOPIC,
                provider="demo",
                max_revisions=1,
                out=args.out,
                search=demo_search(),
                handles=demo_handles(),
            )
        else:
            result = run_research(
                args.topic,
                provider=args.provider,
                max_revisions=args.max_revisions,
                out=args.out,
            )
    except ResearchError as exc:
        print(f"{exc.provider}: {exc.kind}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        try:
            provider = resolve_provider(args.provider)
        except ResearchError as provider_error:
            print(
                f"{provider_error.provider}: {provider_error.kind}: {provider_error}",
                file=sys.stderr,
            )
            return 1
        wrapped = classify_provider_error(provider, exc)
        print(f"{wrapped.provider}: {wrapped.kind}: {wrapped}", file=sys.stderr)
        return 1
    finally:
        reset_status(token)
    print(result.markdown_path)
    return 0


def main() -> None:
    raise SystemExit(run_cli())
