# Evidence-first research agent

A small Python 3.11+ research CLI with explicit planning, three real tool implementations, evidence filtering, structured synthesis, a separate verifier, deterministic offline fixtures, and an agent-versus-baseline evaluation harness. No orchestration framework is required.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m research_agent "Compare the top 3 open-source vector databases for a startup building RAG products." --mock
```

`requirements-lock.txt` records the exact dependency versions used for local verification; install it instead of `requirements.txt` to reproduce that environment. The ranged requirements remain the portable default.

On macOS/Linux use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`. Alternatively activate the environment and use the portable commands below. GNU Make is optional on Windows; each target has a direct Python equivalent.

```sh
python -m pytest -q
python -m evals.run_evals --mock
python scripts/generate_samples.py
```

For live mode, copy `.env.example` to `.env`, set `OPENAI_API_KEY`, and set `OPENAI_MODEL` to a model your account can access that supports structured outputs. The example model is configurable, not an availability guarantee. Set `TAVILY_API_KEY` for Tavily search; without it, discovery uses DuckDuckGo HTML, which may block automated clients. Run the same command without `--mock`. With no LLM key, live mode attempts tools and degrades to extractive synthesis; it does not silently label fixture results as live research.

```sh
python -m research_agent "Compare different approaches to adding memory in an AI support agent." --json
python -m research_agent "Compare vector databases for RAG." --mock --markdown
python -m research_agent "Compare vector databases for RAG." --mock --no-cache --json
python -m research_agent --followup "Which option has filtering?" --mock --json
python -m research_agent "Compare vector databases for RAG." --mock --baseline --json
python -m research_agent "Compare vector databases for RAG." --mock --scenario outage_injection --json
python -m research_agent trace RUN_ID
```

`--session PATH` selects a session (default `.session.json`); `--state-dir PATH` selects the cache/trace directory. Follow-ups reuse the previous question and evidence, which is re-filtered and re-verified. They may refresh promising URLs within the same budget. Sessions are local, last-report memory, not a durable conversation database. Missing sessions return an error without a stack trace. The entry point returns 0 for a completed report, including a low-confidence report, 2 for configuration/file errors, and 130 for interruption.

## Architecture

```text
CLI -> agent.research
         Planner -> Executor -> Filter -> Synthesizer -> Verifier -> ResearchReport
                      |
              web_search / fetch_page / local_kb
                      |
                TTL cache + JSONL spans
```

`research_agent/agent.py` contains the readable orchestration loop. All stage contracts are in `schemas.py`: `Plan`, `ExecutionResult`, `FilterResult`, `Draft`, `Judgment`, and `ResearchReport`. The report includes question, answer, findings with source IDs and support levels, sources and retrieval times, confidence, assumptions, limitations, next steps, and run/cost metadata. `cli.py` renders the validated report. `docs/DESIGN.md` is the one-page risk analysis.

A tool-call budget counts invocations, including cache hits; each invocation can make at most two attempts. LLM transport retry and a single schema repair are separately bounded. `asyncio.timeout` bounds tool calls and the global run. The executor fetches up to three promising URLs concurrently after discovery, with no recursive crawl. A deadline hit returns a conservative report from evidence gathered so far. Failed calls do not become cached successes.

## The seven design questions

### 1. Why an agentic approach?

Research requires deciding whether discovery, primary-page retrieval, or conceptual background is useful, then qualifying incomplete evidence. `planner.py` emits typed sub-questions and tool choices; `executor.py` chooses promising URLs from results. A single LLM call cannot verify fresh external information. `baseline.py` provides exactly that no-tool comparator, with findings marked unverified. The system is deliberately bounded: it does not recursively replan or impersonate a multi-agent team.

### 2. What tools were used and why?

- `tools/web_search.py`: Tavily API, or DuckDuckGo HTML without a Tavily key, discovers sources. Explicit mock mode uses deterministic corpus-based fixtures. Search choice and fallback reasons appear in traces.
- `tools/fetch_page.py`: streamed HTTP(S) fetches retrieve text beyond snippets. Standard-library HTML parsing suppresses navigation/scripts/styles; this is a lightweight readability heuristic, not full browser rendering. It caps decompressed bytes at 500 KB and extracted text at 30,000 characters, allows text/HTML only, and validates every redirect hop.
- `tools/local_kb.py`: keyword retrieval over 12 authored JSON notes provides deterministic conceptual background and offline fallback. Their URLs point to suggested primary reading; notes are not quotations or verified extracts from those URLs. `origin=local` caps authority and confidence; all mock content is labelled synthetic/offline.

All tools implement `Tool.run(ToolInput) -> ToolOutput` in `tools/base.py`, with validation, timeout, retry, trace and cache behavior. Retrieved text cannot create tool names, alter budgets or modify the plan. An initial planner fetch URL must occur in the user question; subsequent fetches come from search results or prior session sources.

### 3. How are bad tool results handled?

`tools/base.py` validates all results and retries transient failures or malformed schema output once. `llm.py` validates Pydantic structured outputs and allows one repair attempt; exhausted planning repairs use a typed rule-based plan. Search errors are recorded as limitations. Local notes and exact-excerpt synthesis allow a report even if search or the LLM fails. No-results queries produce an explicit low-confidence answer and next steps. Invalid/unsafe URLs fail closed.

`filtering.py` drops low-relevance, low-authority, too-short and suspicious results, logs why, and de-duplicates canonical URLs and domains. Unknown publication dates receive a low freshness score: fetching a document today does not make its contents current. Quarantining a fetched page also rejects an earlier innocent-looking snippet at the same URL.

### 4. How are hallucinations reduced?

`synthesizer.py` supplies only retained evidence, with explicit untrusted-data boundaries. Every finding requires source IDs. `verifier.py` rejects nonexistent citations and explicitly unverified findings, then runs a separate entailment judgment. If the judge fails, only exact source excerpts survive. The short answer is rebuilt from approved findings so an unsupported narrative cannot bypass finding checks. Fewer than `MIN_GOOD_SOURCES` cited, independent sources meeting the authority threshold forces low confidence. Mock reports are always low-confidence. Time-sensitive questions without dated evidence are also low-confidence.

This reduces unsupported claims; citation existence and LLM judging do not prove factual truth. Injection regexes are defense in depth, not complete protection against semantic attacks. The baseline is explicitly ungrounded rather than assigned fabricated citations.

### 5. How would this be made production-ready?

Add authenticated API access, tenant-isolated encrypted state, vetted search contracts, configurable egress allowlists at an outbound proxy, secret management, redaction and retention controls, rate limits, concurrency admission, circuit breakers, request cancellation, and explicit spend limits. Replace local files with transactional storage and make session writes concurrency-safe. Use a dedicated readability parser/browser service where needed. Establish audited corpora, benchmark retrieval and ranking on human-labelled questions, calibrate confidence against factual accuracy, and gate releases on adversarial and workload-specific evals. Deploy behind resource limits and test real providers, DNS/TLS behavior and operational recovery. The optional FastAPI endpoint is intentionally omitted to keep this CLI submission focused.

### 6. What would be monitored in production?

`tracing.py` writes `runs/<run_id>.jsonl`, with stage/tool durations, status, retries, input summaries, tool-selection reasons, filtering decisions, token usage and estimated cost. The trace viewer prints these records. Map run IDs to OpenTelemetry trace IDs, stages/tool calls to spans, and source/usage decisions to span events; an exporter could forward this to Langfuse or an OTel collector without changing orchestration.

Monitor tool error/timeout/retry rates, provider throttling, cache hits and stale-hit rate, p50/p95 end-to-end and stage latency, tokens and cost per query, budget exhaustion, low-confidence/abstention rate, invalid/unsupported citation rate, source-quality ratio, source diversity, injection flag rate, session errors, and human-rated task completion. Alert on increases relative to a calibrated baseline, not on isolated low-confidence answers. Traces can contain user questions and source URLs; restrict access and add redaction before production.

### 7. What were the key tradeoffs?

| Decision | Benefit | Cost / limitation |
|---|---|---|
| Single agent with explicit stages vs multiple agents | Simple control flow, lower coordination overhead | Less independent exploration |
| Lexical relevance + domain authority heuristics vs model ranking | Cheap, inspectable and reproducible | Weak synonym handling; domain reputation is not truth |
| Three concurrent page fetches vs deep crawling | Bounded latency and calls | Can miss important sources or requested coverage |
| Separate judge + structured schema | Better grounding checks and stable output shape | Extra LLM latency/cost; judging remains fallible |
| TTL cache vs live retrieval every time | Lower cost and latency | Can retain stale evidence; `--no-cache` bypasses it |
| Local notes vs failure-only answers | Offline continuity and testability | Incomplete authored background, never current verification |
| Domain de-duplication vs retaining all pages | Reduces correlated evidence | Drops useful distinct pages on one host |
| Fail-closed confidence vs optimistic ranking | Honest missing evidence | Mock/extractive output is less polished and less complete |

## Evaluation and sample outputs

`evals/queries.yaml` defines 12 queries, including the four assignment examples, ambiguous/no-results/current/out-of-scope questions and adversarial/provider faults. `evals/run_evals.py` compares agent and no-tool baseline, writes measured latency, tokens, optional estimated cost, citation validity, grounded-finding ratio, source quality, injection checks and topic/coverage proxies to `evals/results.json`. It returns nonzero on regression failures. Empty citation sets produce `null` validity and zero grounded coverage; they do not receive a perfect grounding score. A passing regression is not evidence of complete factual answers.

```sh
make test
make eval
make samples
# Optional, incurs provider costs and uses real search:
python -m evals.run_evals --live --output evals/live_results.json
```

`docs/EVALUATION.md` remains a template as requested; all results and observations there must be filled manually after a run. Machine results are saved separately. `docs/VERIFICATION.md` records actual local verification output; regenerate it with `python scripts/verify.py`. `docs/sample_outputs/FORMAT_EXAMPLE.md` is explicitly illustrative. `python scripts/generate_samples.py` generates three real offline reports (JSON and Markdown) with actual run IDs and measurements; their headers identify mock execution. `docs/DEMO_SCRIPT.md` provides a four-minute recording plan. CI runs tests and mock evaluation without API keys.

## Configuration and accounting

See `.env.example` and `config.py` for model, timeouts, budgets, cache TTL and source threshold. `INPUT_USD_PER_MILLION` and `OUTPUT_USD_PER_MILLION` are optional user-supplied model rates. Cost is `null` when rates are absent; mock cost is zero. Usage is taken from returned API responses, not estimated tokens. Failed responses that never expose usage may incur costs not captured here. Model-side output is capped at 2,500 tokens per call; this is not a hard dollar budget. Default LLM timeout is 20 seconds, tool timeout 8 seconds, global budget 90 seconds and tool-call budget 8.

The SDK interface follows [official OpenAI structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs). The included corpus consists of authored explanatory notes; external URLs are pointers, not a claim of downloaded research.

## Known limitations

- Mock synthesis is extractive and deterministic, not a simulated claim of real LLM research quality. It cannot reliably produce a complete top-three ranking or five verified current startups. Live answer completeness requires human assessment.
- A live read-only smoke test fetched the Qdrant documentation page successfully; DuckDuckGo returned no usable results (possible bot challenge), exercising its warning path. No paid-provider end-to-end result is claimed by the offline suite. SDK, HTTP, retry and URL safety boundaries have isolated tests; real account access and provider behavior need a live smoke test.
- Source publication dates are optional and currently usually unknown. Undated primary web evidence caps confidence at medium; current facts without dated evidence force low confidence.
- Keyword matching, domain heuristics, one-page-per-domain de-duplication and regex injection detection have false positives/negatives. A public website can still publish false information or contain semantic injection.
- HTML extraction has no JavaScript rendering, PDF handling or advanced boilerplate removal. DuckDuckGo markup can change or return bot challenges. Source language support is primarily English.
- DNS pinning checks every returned address and connects only to a checked IP with hostname SNI. Production should still enforce network egress policy. TLS/redirect tests use mocked transport; real TLS needs deployment testing.
- A cancelled DNS lookup runs in a worker thread and may finish after coroutine cancellation; it cannot initiate a fetch, but process shutdown may wait for the platform resolver. File writes and extraction are bounded synchronous work, so the global deadline is a soft wall-clock limit.
- Cache/session/trace files are plaintext local artifacts. Atomic writes avoid torn files, but shared-session concurrent writers are last-writer-wins. Follow-up history grows until the input-length bound is reached. No shared multi-tenant storage or cache eviction beyond TTL reads.
- Planner success criteria are visible guidance; they are not separately executed assertions. The verifier checks citation support and evidence quantity, not full task completion. The executor is a bounded single discovery pass with fallback, not an adaptive deep-research loop.
- Tests/evaluation here validate engineering mechanics and proxies, not source truth, semantic injection resistance or production-grade calibration.

## Future improvements

Add a labelled answer-quality dataset and human review, dated source metadata extraction, primary-source policies per question type, real-provider contract tests, stronger relevance retrieval, quote-level citation spans, question-specific completion checks, bounded replanning for missing coverage, and calibrated uncertainty. Production infrastructure should follow the deployment work described above.

## Run it

From a fresh clone, in PowerShell:

```powershell
cd path\to\research-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m research_agent "Compare the top 3 open-source vector databases for a startup building RAG products." --mock --json
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evals.run_evals --mock
.\.venv\Scripts\python.exe scripts/generate_samples.py
```

| Requirement | Implementation |
|---|---|
| Accept question, plan, select tools and gather evidence | `cli.py`, `planner.py`, `executor.py` |
| Three schema-validated tools | `tools/base.py`, `web_search.py`, `fetch_page.py`, `local_kb.py` |
| Source filtering, scoring and de-duplication | `filtering.py` |
| Structured grounded report and confidence guardrail | `schemas.py`, `synthesizer.py`, `verifier.py` |
| Timeouts, retry, repair, budgets, graceful failure | `llm.py`, `tools/base.py`, `agent.py` |
| SSRF protection and injection awareness | `safety.py`, `fetch_page.py`, `tests/test_safety.py`, malicious fixtures |
| Cache and last-report follow-up memory | `cache.py`, `schemas.Session`, `cli.py` |
| Async execution and logging/tracing | `executor.py`, `tracing.py`, `cli.py` trace command |
| No-tool baseline and evaluation framework | `baseline.py`, `evals/run_evals.py`, `queries.yaml` |
| Offline mock mode, fault fixtures, CI | `data/fixtures/`, `tests/`, `.github/workflows/ci.yml` |
| Twelve local documents | `data/*.json` |
| Evaluation template and demo video plan | `docs/EVALUATION.md`, `docs/DEMO_SCRIPT.md` |
| Three sample reports and illustrative format | `scripts/generate_samples.py`, `docs/sample_outputs/` |
| Full file contents in dependency order | `docs/FULL_SOURCE.md`, generated by `scripts/build_submission.py` |
