from typing import Literal
from pydantic import BaseModel, Field

ClauseVerdict = Literal[
    "COMPLIANT",
    "NEEDS_REVIEW",
    "NON_COMPLIANT",
    "UNCERTAIN_MANUAL_REVIEW",
]


class ExtractedClause(BaseModel):
    clause_id: str
    clause_type: str
    clause_text: str


class ExtractedClauses(BaseModel):
    clauses: list[ExtractedClause]


class RegulatoryCitation(BaseModel):
    source_title: str = Field(description="Regulation/circular title supplied by retrieval metadata.")
    page_number: int | None = Field(default=None, ge=1)
    excerpt: str = Field(description="Relevant retrieved regulatory excerpt supporting the clause verdict.")


class ClauseAnalysis(BaseModel):
    clause_id: str
    clause_type: str
    clause_text: str
    matching_source_rules: list[str] = Field(default_factory=list)
    citations: list[RegulatoryCitation] = Field(default_factory=list)
    verdict: ClauseVerdict = "UNCERTAIN_MANUAL_REVIEW"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis: str
    risk: str
    recommendation: str


class ContractAnalysis(BaseModel):
    final_results: list[ClauseAnalysis]
