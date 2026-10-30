<!-- Actual offline mock run; not current research. -->
# Research report

Compare vector database options for startup RAG products.

**Confidence: LOW** — 5 cited sources meet the authority threshold; entailment judging is heuristic. Insufficient verified independent evidence, mock mode, or verification issues. Curated local notes are not live verification; confidence is capped at medium.

## Short answer

LOW CONFIDENCE: Weaviate is an open-source vector database supporting hybrid keyword and vector search for RAG retrieval. pgvector adds vector similarity search to PostgreSQL, allowing a startup to keep relational data and RAG embeddings together. Qdrant is an open-source vector database with payload filtering and vector similarity search for RAG retrieval.

## Key findings

- Weaviate is an open-source vector database supporting hybrid keyword and vector search for RAG retrieval. [S90899f0e4c] (partial)

- pgvector adds vector similarity search to PostgreSQL, allowing a startup to keep relational data and RAG embeddings together. [Sc5f2c6c39c] (partial)

- Qdrant is an open-source vector database with payload filtering and vector similarity search for RAG retrieval. [S5d131ce421] (partial)

- A RAG vector database comparison should measure recall, latency, ingestion behavior, filtering correctness, and operations under representative workloads. [Sf110ffbdbe] (partial)

- Milvus is an open-source vector database oriented toward scalable similarity search and RAG retrieval. [S4787f38d03] (partial)

## Sources

- [S90899f0e4c: Weaviate vector database — curated background note](https://weaviate.io/developers/weaviate) — relevance 1.00, authority 0.55, used=True, retrieved 2026-10-30T02:35:40.496990+00:00

- [Sc5f2c6c39c: pgvector retrieval — curated background note](https://github.com/pgvector/pgvector) — relevance 0.80, authority 0.55, used=True, retrieved 2026-10-30T02:35:40.495989+00:00

- [S5d131ce421: Qdrant vector database — curated background note](https://qdrant.tech/documentation/) — relevance 0.80, authority 0.55, used=True, retrieved 2026-10-30T02:35:40.495989+00:00

- [Sf110ffbdbe: RAG retrieval benchmark design — curated design note](https://www.postgresql.org/docs/current/textsearch.html) — relevance 0.80, authority 0.55, used=True, retrieved 2026-10-30T02:35:40.495989+00:00

- [S4787f38d03: Milvus vector database — curated background note](https://milvus.io/docs) — relevance 0.80, authority 0.55, used=True, retrieved 2026-10-30T02:35:40.495989+00:00

## Assumptions

- No budget, workload, or deployment constraints were supplied.

## Limitations

- Extractive fallback summarizes source excerpts, not an exhaustive comparison or verified ranking; requested counts may be unmet.

- web_search failed after bounded attempts; see trace

- Filtered 1 unsafe or weak source results

- Offline mock run: fixture content is not current web research

- Local corpus contains authored background notes, not freshly fetched primary evidence

## Next steps

- Verify primary sources and benchmark against your workload.

- Gather additional independent primary evidence before deciding.

Run `01ac7eebbdfc44bfbe9279f548471897` | 3 tool calls | 151 ms | tokens {'input': 0, 'output': 0} | estimated USD 0.0
