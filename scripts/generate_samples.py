"""Generate three actual offline reports. No hand-written result numbers."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_agent.agent import research
from research_agent.cache import atomic_write
from research_agent.cli import markdown
from research_agent.config import Settings


async def main():
    for name, question, scenario in [
        ("vector", "Compare the top 3 open-source vector databases for a startup building RAG products.", "good"),
        ("memory", "Compare different approaches to adding memory in an AI support agent.", "good"),
        ("outage", "Compare vector database options for startup RAG products.", "outage_injection"),
    ]:
        settings = Settings(mock=True, no_cache=True, scenario=scenario, tool_timeout=0.03)
        report, _ = await research(question, settings)
        root = Path("docs/sample_outputs")
        atomic_write(root / f"{name}.json", report.model_dump_json(indent=2))
        atomic_write(root / f"{name}.md", "<!-- Actual offline mock run; not current research. -->\n" + markdown(report))
        print(f"Generated {name}: {report.metadata.run_id}")


if __name__ == "__main__":
    asyncio.run(main())
