import asyncio
import time
from .cache import Cache
from .config import Settings
from .filtering import score
from .safety import canonical, suspicious
from .schemas import Evidence, ExecutionResult, Plan, ToolInput
from .tools.fetch_page import FetchPage
from .tools.local_kb import LocalKB
from .tools.web_search import WebSearch
from .tracing import Trace


class Executor:
    def __init__(self, settings: Settings, trace: Trace, cache: Cache, deadline: float):
        self.settings, self.trace, self.deadline = settings, trace, deadline
        self.tools = {tool.name: tool(settings, trace, cache) for tool in (WebSearch, FetchPage, LocalKB)}
        self.result = ExecutionResult()

    async def call(self, name: str, request: ToolInput, reason: str, budget: int):
        if self.result.steps_taken >= budget or time.perf_counter() >= self.deadline:
            self.result.limitations.append("Research step or time budget exhausted")
            return
        self.result.steps_taken += 1
        if name not in self.result.tools_used:
            self.result.tools_used.append(name)
        self.trace.event("tool_choice", tool=name, reasoning=reason)
        output = await self.tools[name].run(request)
        self.result.evidence.extend(output.documents)
        self.result.limitations.extend(output.warnings)

    async def execute(self, question: str, plan: Plan, prior: list[Evidence]) -> ExecutionResult:
        budget = min(plan.max_steps, self.settings.max_steps)
        self.result.evidence.extend(prior)
        for step in plan.steps:
            if step.tool == "fetch_page" and (not step.url or step.url not in question):
                self.result.limitations.append("Skipped fetch URL not supplied by user or search")
                continue
            await self.call(step.tool, ToolInput(query=step.sub_question, url=step.url),
                            step.reasoning, budget)
        # Always reserve an available slot for offline fallback when discovery produced nothing.
        if not self.result.evidence and "local_kb" not in self.result.tools_used:
            await self.call("local_kb", ToolInput(query=question), "Search failed: offline fallback", budget)
        candidates = []
        seen = set()
        for doc in sorted(self.result.evidence, key=lambda d: score(question, d).relevance_score, reverse=True):
            if doc.origin == "local" or canonical(doc.url) in seen or suspicious(doc.text):
                continue
            if score(question, doc).relevance_score < 0.12:
                continue
            seen.add(canonical(doc.url))
            candidates.append(doc.url)
        if self.settings.mock and self.settings.scenario in {"injection", "outage_injection"}:
            # Fault injection deliberately exercises a hostile page despite the fetch fan-out cap.
            hostile = "https://fixture.example/malicious"
            candidates = [hostile] + [url for url in candidates if url != hostile]
        remaining = max(0, budget - self.result.steps_taken)
        await asyncio.gather(*(self.call("fetch_page", ToolInput(query=question, url=url),
            "Promising discovered URL: retrieve evidence before synthesis", budget)
            for url in candidates[:min(3, remaining)]))
        return self.result
