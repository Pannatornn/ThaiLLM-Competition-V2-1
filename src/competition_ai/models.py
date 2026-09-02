from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Evidence:
    id: str
    source: str
    page: int | None
    text: str
    program: str
    score: float = 0.0
    kind: str = "page"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"{self.source} • หน้า {self.page}" if self.page else self.source

@dataclass
class RouteResult:
    programs: list[str]
    ambiguous: bool = False
    comparison: bool = False
    reason: str = ""

@dataclass
class QueryPlan:
    intent: str = "unknown"
    programs: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    subjective: bool = False
    needs_comparison: bool = False
    requires_exact_number: bool = False
    needs_course_lookup: bool = False
    language: str = "th"

@dataclass
class Verification:
    status: str
    confidence: float = 0.0
    rationale: str = ""
    unsupported_claims: list[str] = field(default_factory=list)
    supported_claims: list[str] = field(default_factory=list)

@dataclass
class AnswerResult:
    status: str
    answer: str
    programs: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    verification: Verification | None = None
    plan: QueryPlan | None = None
    latency_ms: int = 0
    cache_hit: bool = False
    debug: dict[str, Any] = field(default_factory=dict)
