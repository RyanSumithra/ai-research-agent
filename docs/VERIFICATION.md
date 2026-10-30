# Actual local verification

This file records executed commands. The evaluation template remains unfilled. Offline passes do not establish factual quality.

Recorded at: 2026-10-30T02:35:30.342916+00:00

Python: 3.11.0; platform: Windows-10-10.0.26200-SP0

## `python -m pytest -q`

Exit code: 0

```text
...............................................                          [100%]
47 passed in 4.70s
```

## `python -m evals.run_evals --mock`

Exit code: 0

```text
24/24 regression checks passed; saved evals/results.json
```

## `python scripts/generate_samples.py`

Exit code: 0

```text
Generated vector: 696597fec3884384baa0ca6a081b26ba
Generated memory: 8d9e7f4d9f8b458b98d50b0baca49ce1
Generated outage: 01ac7eebbdfc44bfbe9279f548471897
```

## `python -m compileall -q research_agent tests evals scripts`

Exit code: 0

```text

```

## Dependency versions

```text
pydantic==2.14.2
httpx==0.28.1
openai==2.54.0
python-dotenv==1.2.4
rich==14.3.4
pytest==9.2.0
PyYAML==6.0.3
```

## Provider validation boundary

A separate read-only smoke test successfully retrieved the Qdrant documentation page through the DNS-pinned fetcher. DuckDuckGo returned no usable results with a possible bot-challenge warning. OpenAI and Tavily have isolated contract tests but no account-backed live run is claimed.

## Interpretation

The mock suite validates typed orchestration, citation references, failure handling and explicit adversarial fixtures. It does not validate factual completeness, semantic injection resistance, real-provider availability or calibrated confidence. See docs/EVALUATION.md for the review template.
