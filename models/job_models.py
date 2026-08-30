from pydantic import BaseModel

from models.job_status_model import JobStatus


class JobClauseAnalysis(BaseModel):
    """
    Mirrors models.clause_model.ClauseAnalysis, except the source-matching
    field is named to match the frontend's ClauseAnalysis type
    (matching_clause_rules, not matching_source_rules). Kept as a separate
    model so models/clause_model.py doesn't need to change for existing
    consumers.
    """

    clause_id: str
    clause_type: str
    clause_text: str
    matching_clause_rules: list[str]
    analysis: str
    risk: str
    recommendation: str


class UploadJobResponse(BaseModel):
    doc_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    doc_id: str
    status: JobStatus
    original_file_name: str
    error: str | None = None


class JobReportResponse(BaseModel):
    doc_id: str
    results: list[JobClauseAnalysis]


class JobStreamPayload(BaseModel):
    status: JobStatus
    results: list[JobClauseAnalysis] | None = None
    error: str | None = None
