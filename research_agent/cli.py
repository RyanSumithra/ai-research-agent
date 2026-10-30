import argparse
import asyncio
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from .agent import research
from .cache import atomic_write
from .config import Settings
from .schemas import ResearchReport, Session


def markdown(report: ResearchReport) -> str:
    lines = [f"# Research report\n\n{report.question}",
             f"**Confidence: {report.confidence.level.upper()}** — {report.confidence.reasoning}",
             "## Short answer\n\n" + report.short_answer, "## Key findings"]
    lines.extend(f"- {f.claim} [{', '.join(f.evidence_source_ids)}] ({f.support})" for f in report.key_findings)
    lines.append("## Sources")
    lines.extend(f"- [{s.id}: {s.title}]({s.url}) — relevance {s.relevance_score:.2f}, "
                 f"authority {s.authority_score:.2f}, used={s.used}, retrieved {s.retrieved_at.isoformat()}"
                 for s in report.sources)
    for heading, values in (("Assumptions", report.assumptions), ("Limitations", report.limitations),
                            ("Next steps", report.next_steps)):
        lines.append("## " + heading)
        lines.extend("- " + value for value in values)
    meta = report.metadata
    lines.append(f"Run `{meta.run_id}` | {meta.steps_taken} tool calls | {meta.latency_ms:.0f} ms | "
                 f"tokens {meta.token_usage} | estimated USD {meta.est_cost_usd}")
    return "\n\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-first research agent")
    parser.add_argument("question", nargs="?")
    parser.add_argument("trace_id", nargs="?", help="For: trace RUN_ID")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", action="store_true", help="Print raw Markdown")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--followup")
    parser.add_argument("--session", type=Path, default=Path(".session.json"))
    parser.add_argument("--state-dir", type=Path, default=Path("."))
    parser.add_argument("--scenario", choices=["good", "empty", "malformed", "timeout", "injection",
                                             "spam", "outage_injection"], default="good")
    args = parser.parse_args(argv)
    try:
        if args.question == "trace":
            if not args.trace_id or not args.trace_id.isalnum():
                raise ValueError("trace requires an alphanumeric run ID")
            path = args.state_dir / "runs" / f"{args.trace_id}.jsonl"
            for line in path.read_text(encoding="utf-8").splitlines():
                Console().print_json(line)
            return 0
        question, prior = args.question, []
        if args.followup:
            session = Session.model_validate_json(args.session.read_text(encoding="utf-8"))
            question = f"Original question: {session.report.question}\nFollow-up: {args.followup}"
            prior = session.evidence
        if not question:
            raise ValueError("Supply a question or --followup")
        settings = Settings.from_env(mock=args.mock, no_cache=args.no_cache,
                                     state_dir=args.state_dir, scenario=args.scenario)
        if args.scenario != "good" and not args.mock:
            raise ValueError("Fault scenarios require --mock")
        if args.mock and args.scenario in {"timeout", "outage_injection"}:
            settings.tool_timeout = min(settings.tool_timeout, 0.05)
        report, evidence = asyncio.run(research(question, settings, prior=prior, use_baseline=args.baseline))
        atomic_write(args.session, Session(report=report, evidence=evidence).model_dump_json(indent=2))
        if args.json:
            print(report.model_dump_json(indent=2))
        elif args.markdown:
            print(markdown(report))
        else:
            Console().print(Markdown(markdown(report)))
        return 0
    except KeyboardInterrupt:
        print("Research cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Research could not complete ({type(exc).__name__}). Check arguments, files and configuration.",
              file=sys.stderr)
        return 2
