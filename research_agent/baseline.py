from .llm import LLM
from .schemas import Confidence, Draft, Finding


async def baseline(question: str, llm: LLM) -> tuple[Draft, Confidence]:
    mock = Draft(short_answer="No-tool baseline cannot verify external facts.",
        key_findings=[Finding(claim="A workload benchmark is needed before selecting a vector database.",
                      evidence_source_ids=[], support="unverified")], assumptions=[],
        limitations=["No retrieval; all factual claims are unverified."],
        next_steps=["Run the research workflow to obtain citations."])
    try:
        draft = await llm.generate(Draft,
            "Answer without tools. Do not invent sources or source IDs. Mark all findings unverified.",
            {"question": question}, mock)
    except Exception:
        draft = mock
    for finding in draft.key_findings:
        finding.evidence_source_ids, finding.support = [], "unverified"
    draft.short_answer = "LOW CONFIDENCE (no-tool baseline): " + draft.short_answer
    return draft, Confidence(level="low", reasoning="No external evidence was retrieved or verified.")
