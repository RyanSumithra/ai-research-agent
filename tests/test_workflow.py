import asyncio
import json
import subprocess
import sys
import pytest
from research_agent.agent import research
from research_agent.cli import main
from research_agent.llm import LLM
from research_agent.planner import create_plan
from research_agent.schemas import Draft, Evidence, Finding, ResearchReport
from research_agent.verifier import verify

QUESTION = "Compare the top 3 open-source vector databases for a startup building RAG products."


def test_end_to_end_report_and_trace(settings):
    report, evidence = asyncio.run(research(QUESTION, settings))
    ResearchReport.model_validate_json(report.model_dump_json())
    assert len(report.sources) >= 3
    assert report.key_findings
    ids = {s.id for s in report.sources}
    assert all(f.evidence_source_ids and set(f.evidence_source_ids) <= ids for f in report.key_findings)
    assert set(report.metadata.tools_used) == {"web_search", "local_kb", "fetch_page"}
    assert report.metadata.steps_taken <= settings.max_steps
    assert report.confidence.level == "low"
    trace = settings.state_dir / "runs" / f"{report.metadata.run_id}.jsonl"
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    for stage in ("planner", "executor", "filter", "synthesizer", "verifier"):
        assert any(e["name"] == stage for e in events)


@pytest.mark.parametrize("scenario", ["empty", "timeout", "malformed", "injection", "spam", "outage_injection"])
def test_faults_degrade_without_injection(settings, scenario):
    settings.scenario = scenario
    report, _ = asyncio.run(research(QUESTION, settings))
    assert report.confidence.level == "low"
    assert "TOOL_PAYLOAD_SENTINEL" not in report.model_dump_json()
    assert all("seo-spam" not in s.url and "/malicious" not in s.url for s in report.sources)
    if scenario in {"timeout", "malformed", "outage_injection"}:
        assert any("web_search failed" in s for s in report.limitations)
        assert "local_kb" in report.metadata.tools_used
    if scenario == "outage_injection":
        assert any("Filtered" in s for s in report.limitations)


def test_no_results(settings):
    report, _ = asyncio.run(research("zxqv flormble", settings))
    assert not report.sources and not report.key_findings
    assert report.confidence.level == "low"


def test_single_source_guardrail_and_unknown_citation(settings, context):
    llm = LLM(settings, context[0])
    evidence = [Evidence(id="S1", url="https://qdrant.tech", title="Qdrant", text="Qdrant supports filtering.",
                         relevance_score=1, authority_score=0.9)]
    draft = Draft(short_answer="Unsupported marketing claim", key_findings=[
        Finding(claim="Qdrant supports filtering.", evidence_source_ids=["S1"], support="strong"),
        Finding(claim="Invented", evidence_source_ids=["MISSING"], support="strong")],
        assumptions=[], limitations=[], next_steps=[])
    revised, confidence = asyncio.run(verify(draft, evidence, llm))
    assert confidence.level == "low"
    assert len(revised.key_findings) == 1
    assert "Unsupported marketing" not in revised.short_answer


def test_judge_failure_keeps_only_exact_excerpts(settings, context, monkeypatch):
    llm = LLM(settings, context[0])
    async def failed(*args, **kwargs):
        raise ValueError("malformed")
    monkeypatch.setattr(llm, "generate", failed)
    evidence = [Evidence(id="S1", url="https://example.com", title="Example", text="A source fact.")]
    draft = Draft(short_answer="x", key_findings=[Finding(claim="Unfounded assertion.",
        evidence_source_ids=["S1"], support="strong")], assumptions=[], limitations=[], next_steps=[])
    revised, confidence = asyncio.run(verify(draft, evidence, llm))
    assert not revised.key_findings and confidence.level == "low"


def test_planner_failure_uses_typed_fallback(settings, context, monkeypatch):
    llm = LLM(settings, context[0])
    async def failed(*args, **kwargs):
        raise ValueError("invalid after repair")
    monkeypatch.setattr(llm, "generate", failed)
    plan = asyncio.run(create_plan(QUESTION, llm))
    assert {step.tool for step in plan.steps} == {"web_search", "local_kb"}


def test_global_budget_returns_valid_low_report(settings):
    settings.time_budget = 0.001
    settings.scenario = "timeout"
    report, _ = asyncio.run(research(QUESTION, settings))
    assert report.confidence.level == "low"
    assert any("time budget" in note for note in report.limitations)


def test_baseline_no_tools(settings):
    report, _ = asyncio.run(research(QUESTION, settings, use_baseline=True))
    assert not report.sources and not report.metadata.tools_used
    assert all(f.support == "unverified" for f in report.key_findings)


def test_cli_json_session_followup_and_trace(tmp_path, capsys):
    session = tmp_path / "session.json"
    args = ["--mock", "--json", "--state-dir", str(tmp_path), "--session", str(session)]
    assert main([QUESTION, *args]) == 0
    first = ResearchReport.model_validate_json(capsys.readouterr().out)
    assert session.exists()
    assert main(["--followup", "Which has filtering?", *args]) == 0
    followup = ResearchReport.model_validate_json(capsys.readouterr().out)
    assert "Follow-up" in followup.question and followup.sources
    assert main(["trace", first.metadata.run_id, "--state-dir", str(tmp_path)]) == 0
    assert "source_filter" in capsys.readouterr().out


def test_cli_missing_session_no_stacktrace(tmp_path, capsys):
    assert main(["--followup", "anything", "--session", str(tmp_path / "missing")]) == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err and "could not complete" in err


def test_module_entrypoint(tmp_path):
    result = subprocess.run([sys.executable, "-m", "research_agent", QUESTION, "--mock", "--json",
        "--state-dir", str(tmp_path), "--session", str(tmp_path / "session.json")],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    ResearchReport.model_validate_json(result.stdout)
