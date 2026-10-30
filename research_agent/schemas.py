from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")


ToolName = Literal["web_search", "fetch_page", "local_kb"]


class ToolInput(Model):
    query: str = Field(min_length=1, max_length=4000)
    url: str | None = None
    limit: int = Field(default=5, ge=1, le=10)


class Evidence(Model):
    id: str = ""
    url: str
    title: str
    text: str = Field(max_length=30000)
    retrieved_at: datetime = Field(default_factory=now)
    published_at: datetime | None = None
    origin: Literal["web", "local", "mock"] = "web"
    relevance_score: float = Field(default=0, ge=0, le=1)
    authority_score: float = Field(default=0, ge=0, le=1)
    freshness_score: float = Field(default=0, ge=0, le=1)


class ToolOutput(Model):
    documents: list[Evidence] = Field(default_factory=list, max_length=10)
    warnings: list[str] = Field(default_factory=list)


class Step(Model):
    sub_question: str = Field(min_length=1, max_length=4000)
    tool: ToolName
    reasoning: str
    url: str | None = None


class Plan(Model):
    steps: list[Step] = Field(min_length=1, max_length=10)
    success_criteria: list[str]
    max_steps: int = Field(ge=1, le=12)


class ExecutionResult(Model):
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    steps_taken: int = 0
    tools_used: list[str] = Field(default_factory=list)


class FilterResult(Model):
    retained: list[Evidence]
    rejected: list[str]


class Finding(Model):
    claim: str = Field(min_length=1, max_length=2000)
    evidence_source_ids: list[str]
    support: Literal["strong", "partial", "unverified"]


class Draft(Model):
    short_answer: str
    key_findings: list[Finding]
    assumptions: list[str]
    limitations: list[str]
    next_steps: list[str]


class Judgment(Model):
    supported_finding_indices: list[int]
    issues: list[str]


class Source(Model):
    id: str
    url: str
    title: str
    retrieved_at: datetime
    relevance_score: float = Field(ge=0, le=1)
    authority_score: float = Field(ge=0, le=1)
    used: bool


class Confidence(Model):
    level: Literal["high", "medium", "low"]
    reasoning: str


class Metadata(Model):
    run_id: str
    steps_taken: int
    tools_used: list[str]
    latency_ms: float = Field(ge=0)
    token_usage: dict[str, int]
    est_cost_usd: float | None = Field(ge=0)


class ResearchReport(Model):
    question: str
    short_answer: str
    key_findings: list[Finding]
    sources: list[Source]
    confidence: Confidence
    assumptions: list[str]
    limitations: list[str]
    next_steps: list[str]
    metadata: Metadata


class Session(Model):
    report: ResearchReport
    evidence: list[Evidence]
