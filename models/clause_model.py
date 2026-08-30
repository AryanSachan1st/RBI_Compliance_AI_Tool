from pydantic import BaseModel


class ExtractedClause(BaseModel):
    clause_id: str
    clause_type: str
    clause_text: str


class ExtractedClauses(BaseModel):
    clauses: list[ExtractedClause]


class ClauseAnalysis(BaseModel):
    clause_id: str
    clause_type: str
    clause_text: str
    matching_source_rules: list[str]
    analysis: str
    risk: str
    recommendation: str


class ContractAnalysis(BaseModel):
    final_results: list[ClauseAnalysis]
