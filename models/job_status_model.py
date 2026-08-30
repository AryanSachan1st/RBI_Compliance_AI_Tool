from enum import Enum


class JobStatus(str, Enum):
    """
    Short status codes for the async job-based document analysis flow
    (routes/analysis_job_routes.py).

    This is a separate enum from models/pipeline_status_model.py on purpose:
    that one holds the human-readable sentences used by the original
    synchronous /upload-doc/ SSE endpoint, and that endpoint is left
    untouched. These codes instead mirror the UI's `DocStatus` type
    (src/types/api.ts) so the two sides speak the same values without
    the frontend needing to translate anything.
    """

    QUEUED = "QUEUED"
    EXTRACTING_CLAUSES = "EXTRACTING_CLAUSES"
    SEARCHING_SOURCES = "SEARCHING_SOURCES"
    GENERATING_RESPONSE = "GENERATING_RESPONSE"
    DONE = "DONE"
    FAILED = "FAILED"
