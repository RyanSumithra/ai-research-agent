"""Build full-file Markdown and a source ZIP, excluding secrets and runtime state."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["research_agent/schemas.py", "research_agent/config.py", "research_agent/tracing.py",
         "research_agent/cache.py", "research_agent/llm.py", "research_agent/tools/base.py",
         "research_agent/tools/web_search.py", "research_agent/tools/fetch_page.py",
         "research_agent/tools/local_kb.py", "research_agent/safety.py", "research_agent/planner.py",
         "research_agent/executor.py", "research_agent/filtering.py", "research_agent/synthesizer.py",
         "research_agent/verifier.py", "research_agent/baseline.py", "research_agent/agent.py",
         "research_agent/cli.py", "research_agent/__init__.py", "research_agent/__main__.py",
         "research_agent/tools/__init__.py"]
ROOT_FILES = ["README.md", "requirements.txt", "requirements-lock.txt", "pyproject.toml",
              ".env.example", ".gitignore", "Makefile"]


def inputs() -> list[Path]:
    files = [ROOT / name for name in ROOT_FILES if (ROOT / name).exists()]
    for folder in ("research_agent", "data", "tests", "evals", "docs", "scripts", ".github"):
        files.extend(path for path in (ROOT / folder).rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts and path.suffix != ".pyc"
                     and path.name != "FULL_SOURCE.md")
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    files = inputs()
    lookup = {path.relative_to(ROOT).as_posix(): path for path in files}
    groups = [
        ("Phase 2 â€” implementation and configuration", ORDER + [key for key in lookup
         if key not in ORDER and (key.startswith("data/") or key in ROOT_FILES and key != "README.md")]),
        ("Phase 3 â€” tests, evaluation harness and reproducibility scripts", [key for key in lookup
         if key.startswith(("tests/", "evals/", "scripts/", ".github/"))]),
        ("Phase 4 â€” README", ["README.md"]),
        ("Phase 5 â€” evaluation template and sample reports", [key for key in lookup
         if key.startswith("docs/") and key not in ("docs/DESIGN.md", "docs/DEMO_SCRIPT.md")]),
        ("Phase 6 â€” four-minute demo plan", ["docs/DEMO_SCRIPT.md"]),
    ]
    listing = ["# Complete project source", "Every authored file is included below in full. "
               "The generated listing itself is excluded to avoid recursive inclusion.",
               "# Phase 1 â€” design", lookup["docs/DESIGN.md"].read_text(encoding="utf-8")]
    included = {"docs/DESIGN.md"}
    for heading, names in groups:
        listing.append("# " + heading)
        for name in names:
            path = lookup[name]
            included.add(name)
            language = {".py": "python", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
                        ".toml": "toml", ".md": "markdown"}.get(path.suffix, "text")
            content = path.read_text(encoding="utf-8")
            fence = "`" * max(4, max((len(line) for line in content.splitlines()
                              if line and set(line) == {"`"}), default=0) + 1)
            listing.extend([f"## {name}", f"{fence}{language}\n{content.rstrip()}\n{fence}"])
    assert included == set(lookup), "Every file must appear exactly once in the full source listing"
    listing.append("# Run it\n\n```powershell\npython -m venv .venv\n"
                   ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
                   '.\\.venv\\Scripts\\python.exe -m research_agent "Compare vector databases for RAG." --mock\n'
                   "```\n\nThe complete requirement-to-file checklist appears in README.md above.")
    source = ROOT / "docs/FULL_SOURCE.md"
    source.write_text("\n\n".join(listing) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ROOT / "submission.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files + [source]:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Packaged {len(files)+1} files; full source: {source}; archive: {ROOT / 'submission.zip'}")


if __name__ == "__main__":
    main()
