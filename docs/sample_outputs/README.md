# Sample output generation

Run from the repository root:

```sh
python scripts/generate_samples.py
```

This writes `vector.json`/`.md`, `memory.json`/`.md`, and `outage.json`/`.md` from three actual offline executions, including measured metadata and trace IDs. These are mock runs over authored fixtures, not current web research. Re-running changes run IDs, timestamps and timing.

Equivalent individual commands:

```sh
python -m research_agent "Compare the top 3 open-source vector databases for a startup building RAG products." --mock --no-cache --json
python -m research_agent "Compare different approaches to adding memory in an AI support agent." --mock --no-cache --json
python -m research_agent "Compare vector database options for startup RAG products." --mock --scenario outage_injection --no-cache --json
```

`FORMAT_EXAMPLE.md` illustrates formatting only and is not a measured run. The evaluation template intentionally remains unfilled even when actual machine outputs exist.
