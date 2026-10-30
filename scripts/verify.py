"""Reproduce local verification and record actual command output separately from the eval template."""
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sections = ["# Actual local verification", "This file records executed commands. "
                "The evaluation template remains unfilled. Offline passes do not establish factual quality.",
                "Recorded at: " + datetime.now(timezone.utc).isoformat(),
                "Python: " + platform.python_version() + "; platform: " + platform.platform()]
    commands = [["-m", "pytest", "-q"], ["-m", "evals.run_evals", "--mock"],
                ["scripts/generate_samples.py"], ["-m", "compileall", "-q", "research_agent", "tests", "evals", "scripts"]]
    for command in commands:
        result = subprocess.run([sys.executable, *command], cwd=ROOT, text=True,
                                encoding="utf-8", errors="replace", capture_output=True)
        output = result.stdout + result.stderr
        print(output, end="")
        sections.extend(["## `python " + " ".join(command) + "`",
                         f"Exit code: {result.returncode}", "```text\n" + output.rstrip() + "\n```"])
        if result.returncode:
            (ROOT / "docs/VERIFICATION.md").write_text("\n\n".join(sections)+"\n", encoding="utf-8")
            return result.returncode
    sections.extend(["## Dependency versions", "```text\n" + "\n".join(
        name + "==" + importlib.metadata.version(name) for name in
        ("pydantic", "httpx", "openai", "python-dotenv", "rich", "pytest", "PyYAML")) + "\n```",
        "## Provider validation boundary",
        "A separate read-only smoke test successfully retrieved the Qdrant documentation page through "
        "the DNS-pinned fetcher. DuckDuckGo returned no usable results with a possible bot-challenge "
        "warning. OpenAI and Tavily have isolated contract tests but no account-backed live run is claimed.",
        "## Interpretation",
        "The mock suite validates typed orchestration, citation references, failure handling and explicit "
        "adversarial fixtures. It does not validate factual completeness, semantic injection resistance, "
        "real-provider availability or calibrated confidence. See docs/EVALUATION.md for the review template."])
    (ROOT / "docs/VERIFICATION.md").write_text("\n\n".join(sections)+"\n", encoding="utf-8")
    print("Saved docs/VERIFICATION.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
