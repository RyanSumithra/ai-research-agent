import hashlib
from urllib.parse import urlsplit
from .safety import canonical, public_url, suspicious, terms
from .schemas import Evidence, FilterResult, now
from .tracing import Trace

OFFICIAL = {"qdrant.tech", "weaviate.io", "milvus.io", "github.com", "docs.python.org",
            "platform.openai.com", "developers.openai.com", "postgresql.org", "arxiv.org"}


def score(question: str, document: Evidence) -> Evidence:
    query = terms(question)
    overlap = len(query & terms(document.title + " " + document.text)) / max(1, len(query))
    host = (urlsplit(document.url).hostname or "").lower()
    authority = 0.85 if any(host == domain or host.endswith("." + domain) for domain in OFFICIAL) else 0.45
    if any(host == d or host.endswith("." + d) for d in ("reuters.com", "nature.com", "acm.org", "ieee.org")):
        authority = 0.7
    if any(host == d or host.endswith("." + d) for d in ("reddit.com", "quora.com")):
        authority = 0.25
    if any(word in host for word in ("spam", "seo", "best-deals")):
        authority = 0.1
    if document.origin == "local":
        authority = min(authority, 0.55)
    freshness = 0.35  # Unknown publication date is not inferred from fetch time.
    if document.published_at:
        age = max(0, (now() - document.published_at).total_seconds() / 86400)
        freshness = 1 if age < 180 else 0.6 if age < 730 else 0.2
    return document.model_copy(update={"relevance_score": round(overlap, 3),
        "authority_score": authority, "freshness_score": freshness})


def filter_sources(question: str, evidence: list[Evidence], trace: Trace) -> FilterResult:
    scored, rejected = [], []
    tainted_urls = {canonical(d.url) for d in evidence if suspicious(d.title + " " + d.text)}
    for doc in evidence:
        reason = None
        try:
            public_url(doc.url)
        except ValueError:
            reason = "unsafe URL"
        if canonical(doc.url) in tainted_urls:
            reason = "prompt injection pattern"
        doc = score(question, doc)
        combined = 0.55*doc.relevance_score + 0.35*doc.authority_score + 0.1*doc.freshness_score
        if not reason and (doc.relevance_score < 0.12 or doc.authority_score < 0.25 or combined < 0.30 or len(doc.text) < 70):
            reason = "weak relevance, authority, or content"
        if reason:
            rejected.append(reason)
            trace.event("source_filter", source_url=canonical(doc.url), status="dropped", reason=reason)
        else:
            scored.append((combined, doc))
    # Prefer full pages over short snippets when the same URL is returned twice.
    scored.sort(key=lambda row: (row[0], len(row[1].text)), reverse=True)
    retained, urls, domains = [], set(), set()
    for _, doc in scored:
        url, domain = canonical(doc.url), urlsplit(doc.url).netloc.lower()
        if url in urls or domain in domains:
            trace.event("source_filter", source_url=url, status="dropped", reason="duplicate URL/domain")
            continue
        urls.add(url)
        domains.add(domain)
        doc.id = "S" + hashlib.sha256(url.encode()).hexdigest()[:10]
        retained.append(doc)
        trace.event("source_filter", source_id=doc.id, status="retained",
                    relevance=doc.relevance_score, authority=doc.authority_score,
                    freshness=doc.freshness_score)
    return FilterResult(retained=retained[:8], rejected=rejected)
