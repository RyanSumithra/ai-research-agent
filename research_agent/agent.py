import asyncio
import time
from .baseline import baseline
from .cache import Cache
from .config import Settings
from .executor import Executor
from .filtering import filter_sources
from .llm import LLM
from .planner import create_plan
from .schemas import Confidence, Evidence, Metadata, ResearchReport, Source
from .synthesizer import extractive_draft, synthesize
from .tracing import Trace
from .verifier import verify


async def research(question: str, settings: Settings, *, prior: list[Evidence] | None = None,
                   use_baseline: bool = False) -> tuple[ResearchReport, list[Evidence]]:
    if not question.strip() or len(question) > 4000:
        raise ValueError("Question must contain 1–4000 characters")
    started = time.perf_counter()
    trace = Trace(settings.state_dir)
    llm = LLM(settings, trace)
    cache = Cache(settings.state_dir, settings.cache_ttl, not settings.no_cache)
    executor = Executor(settings, trace, cache, started + settings.time_budget)
    retained, limitations = [], []
    draft, confidence = extractive_draft([]), Confidence(level="low", reasoning="No verified evidence")
    try:
        async with asyncio.timeout(settings.time_budget):
            if use_baseline:
                with trace.span("baseline"):
                    draft, confidence = await baseline(question, llm)
            else:
                with trace.span("planner"):
                    plan = await create_plan(question, llm)
                trace.event("plan", plan=plan.model_dump())
                with trace.span("executor"):
                    result = await executor.execute(question, plan, prior or [])
                limitations.extend(result.limitations)
                with trace.span("filter"):
                    filtered = filter_sources(question, result.evidence, trace)
                    retained = filtered.retained
                if filtered.rejected:
                    limitations.append(f"Filtered {len(filtered.rejected)} unsafe or weak source results")
                with trace.span("synthesizer"):
                    draft = await synthesize(question, retained, llm)
                with trace.span("verifier"):
                    draft, confidence = await verify(draft, retained, llm, question)
    except Exception as exc:
        trace.event("run_degraded", error=type(exc).__name__)
        limitations.extend(executor.result.limitations)
        limitations.append("Run time budget exhausted" if isinstance(exc, TimeoutError) else
                            "A stage failed; returned conservative extractive evidence")
        retained = filter_sources(question, executor.result.evidence, trace).retained
        draft = extractive_draft(retained)
        draft.short_answer = "LOW CONFIDENCE: Research incomplete; source excerpts are shown below."
        confidence = Confidence(level="low", reasoning="Run incomplete; evidence not fully verified")
    finally:
        await llm.close()
    if settings.mock:
        limitations.append("Offline mock run: fixture content is not current web research")
    if any(doc.origin == "local" for doc in retained):
        limitations.append("Local corpus contains authored background notes, not freshly fetched primary evidence")
    used = {sid for finding in draft.key_findings for sid in finding.evidence_source_ids}
    report = ResearchReport(question=question, short_answer=draft.short_answer,
        key_findings=draft.key_findings,
        sources=[Source(**{key: getattr(doc, key) for key in
                 ("id", "url", "title", "retrieved_at", "relevance_score", "authority_score")},
                 used=doc.id in used) for doc in retained], confidence=confidence,
        assumptions=draft.assumptions, limitations=list(dict.fromkeys(draft.limitations + limitations)),
        next_steps=draft.next_steps,
        metadata=Metadata(run_id=trace.run_id, steps_taken=executor.result.steps_taken,
            tools_used=executor.result.tools_used, latency_ms=round((time.perf_counter()-started)*1000, 2),
            token_usage=llm.tokens, est_cost_usd=llm.cost()))
    trace.event("report", confidence=confidence.level, sources=len(retained),
                latency_ms=report.metadata.latency_ms, tokens=llm.tokens, est_cost_usd=llm.cost())
    return report, retained
