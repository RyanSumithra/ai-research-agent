<!-- Actual offline mock run; not current research. -->
# Research report

Compare the top 3 open-source vector databases for a startup building RAG products.

**Confidence: LOW** — 5 cited sources meet the authority threshold; entailment judging is heuristic. Insufficient verified independent evidence, mock mode, or verification issues.

## Short answer

LOW CONFIDENCE: Qdrant is an open-source vector database with payload filtering and vector similarity search for RAG retrieval. Weaviate is an open-source vector database supporting hybrid keyword and vector search for RAG retrieval. Milvus is an open-source vector database oriented toward scalable similarity search and RAG retrieval.

## Key findings

- Qdrant is an open-source vector database with payload filtering and vector similarity search for RAG retrieval. [S5d131ce421] (partial)

- Weaviate is an open-source vector database supporting hybrid keyword and vector search for RAG retrieval. [S90899f0e4c] (partial)

- Milvus is an open-source vector database oriented toward scalable similarity search and RAG retrieval. [S4787f38d03] (partial)

- pgvector adds vector similarity search to PostgreSQL, allowing a startup to keep relational data and RAG embeddings together. [Sc5f2c6c39c] (partial)

- A RAG vector database comparison should measure recall, latency, ingestion behavior, filtering correctness, and operations under representative workloads. [Sf110ffbdbe] (partial)

## Sources

- [S5d131ce421: Qdrant vector database — curated background note](https://qdrant.tech/documentation/) — relevance 0.83, authority 0.85, used=True, retrieved 2026-10-30T02:35:40.313000+00:00

- [S90899f0e4c: Weaviate vector database — curated background note](https://weaviate.io/developers/weaviate) — relevance 0.83, authority 0.85, used=True, retrieved 2026-10-30T02:35:40.313997+00:00

- [S4787f38d03: Milvus vector database — curated background note](https://milvus.io/docs) — relevance 0.83, authority 0.85, used=True, retrieved 2026-10-30T02:35:40.311979+00:00

- [Sc5f2c6c39c: pgvector retrieval — curated background note](https://github.com/pgvector/pgvector) — relevance 0.50, authority 0.85, used=True, retrieved 2026-10-30T02:35:40.313000+00:00

- [Sf110ffbdbe: RAG retrieval benchmark design — curated design note](https://www.postgresql.org/docs/current/textsearch.html) — relevance 0.50, authority 0.85, used=True, retrieved 2026-10-30T02:35:40.313000+00:00

## Assumptions

- No budget, workload, or deployment constraints were supplied.

## Limitations

- Extractive fallback summarizes source excerpts, not an exhaustive comparison or verified ranking; requested counts may be unmet.

- Offline mock run: fixture content is not current web research

## Next steps

- Verify primary sources and benchmark against your workload.

- Gather additional independent primary evidence before deciding.

Run `696597fec3884384baa0ca6a081b26ba` | 5 tool calls | 23 ms | tokens {'input': 0, 'output': 0} | estimated USD 0.0
