# Phase 1: focused design

```text
Question -> Planner -> Executor -> Filter/Scorer -> Synthesizer -> Verifier -> Report
                         |              |                           |
                  Search/Fetch/KB   Quarantine                Confidence guardrail
                         |
                  TTL cache + JSONL trace
```

Pydantic contracts connect every stage. The planner emits sub-questions, tool choices, reasons, success criteria and a bounded step count. The executor runs discovery steps, consults local notes, then fetches at most three promising search results concurrently. Source text never goes back into the planner. Filtering scores relevance, authority and freshness and de-duplicates by URL/domain. Synthesis uses only retained evidence. A separate judge checks grounded findings; the final short answer is assembled from approved claims. The CLI renders the same report as JSON, Markdown or terminal text. Mock mode follows this same pipeline with authored fixtures and exact-excerpt judgments.

| Risk | Mitigation |
|---|---|
| Unsupported claims and fake citations | Validate IDs; second judge; exact-excerpt fallback; rebuild short answer from approved findings; minimum-source confidence guardrail |
| Retrieved prompt injection | Treat content as untrusted; reject suspicious sources; quarantine all versions of tainted URLs; no source-to-planner feedback |
| SSRF and redirects | Resolve every hop, reject non-public/mixed DNS answers, pin transport IP, retain TLS SNI, disable proxies, cap ports and redirects |
| Outages, malformed output and slow providers | Typed tool boundaries, per-call timeout, one retry, one LLM schema-repair attempt, local/extractive fallback |
| Unbounded work, latency and spend | Global deadline, tool-call budget, bounded fetch fan-out, capped evidence and output tokens, TTL cache and token/cost traces |

This is one agent with explicit stages, not a multi-agent platform. Source scoring, lexical retrieval and judging remain imperfect; mock results demonstrate mechanics rather than factual research quality.
