from pydantic import BaseModel
from typing import List

class ExtractedClause(BaseModel):
    clause_id: str
    clause_type: str
    clause_text: str

class ExtractedClauses(BaseModel):
    clauses: List[ExtractedClause]

class ClauseAnalysis(BaseModel):
    clause_id: str
    clause_type: str
    clause_test: str
    matching_clause_rules: List[str]
    analysis: str
    risk: str
    recommendation: str

class ContractAnalysis(BaseModel):
    final_results: List[ClauseAnalysis]