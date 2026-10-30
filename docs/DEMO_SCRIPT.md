# Four-minute demo video plan

Record the CLI and a code editor. Use an activated environment. These are instructions for recording, not a claim that a video has been recorded.

| Time | Shot / command | Narration |
|---|---|---|
| 0:00–0:20 | Show README architecture and the example question | Explain evidence-first research and why external tools are needed. State this recording uses deterministic offline fixtures. |
| 0:20–0:55 | `python -m research_agent "Compare the top 3 open-source vector databases for a startup building RAG products." --mock` | Show short answer, findings, citations and assumptions. Explain that the corpus supplies candidates, not a verified top-three ranking. Mock confidence is always low. |
| 0:55–1:15 | Run same query with `--mock --json` | Point out stable `ResearchReport` fields, used source flags, token/cost metadata and run ID. No API keys are required for the demo. |
| 1:15–1:45 | `python -m research_agent trace RUN_ID` using the printed ID | Show the plan, tool-choice reasons, search/local retrieval, concurrent page fetches, filtering, synthesis and verifier spans. |
| 1:45–2:25 | `python -m research_agent "Compare vector database options for startup RAG products." --mock --scenario outage_injection --json` | Search times out twice. Local KB supplies background. A seeded hostile page models a URL from a prior/discovered source. Explain that its instructions are quarantined, not executed; show low confidence and limitations. |
| 2:25–2:45 | View that run with `trace RUN_ID` | Find `tool_error`, local fallback, `fetch_page` and `prompt injection pattern` source rejection. Explain why an innocent-looking snippet at the same URL would also be removed. |
| 2:45–3:20 | Open `agent.py`, `schemas.py`, `tools/base.py`, `safety.py` | Walk through the bounded orchestration loop, typed contracts, retries/timeouts, global budget and DNS-pinned fetch. Explain single-agent simplicity. |
| 3:20–3:45 | `python -m pytest -q`; show `python -m evals.run_evals --mock` results file | Show structural/citation/safety checks and comparison against no-tool baseline. Read the real measurements from this run. Do not present template result cells as completed evaluation. |
| 3:45–4:00 | Show README limitations and production monitoring | Name lexical filtering, authored corpus, heuristic judge/injection checks and unvalidated paid-provider behavior. Mention p95 latency, cost/query, tool failures, low-confidence rate and human answer-quality review. |

Preparation: run tests, ensure dependencies are installed, clear sensitive environment values from the screen, and generate samples with `python scripts/generate_samples.py`. Use `--no-cache` for a reproducible first-path trace. For live footage remove `--mock` only after configuring providers; label that recording separately.
