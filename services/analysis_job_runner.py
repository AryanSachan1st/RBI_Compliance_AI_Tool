"""
Runs the same clause-extraction -> retrieval -> analysis pipeline as
services/core_langchain_service.py, but as a fire-and-forget background
task that reports progress into services/job_store.py instead of yielding
SSE chunks directly from an HTTP request. Used exclusively by
routes/analysis_job_routes.py; the original routes/document_routes.py and
its inline run_pipeline() are untouched.
"""

from models.job_status_model import JobStatus
from services import job_store
from services.core_langchain_service import (
    analyze_retrieved_clauses,
    build_analysis_context,
    extract_clauses,
    retrieve_all_chunks,
)


async def run_analysis_job(doc_id: str, doc_text: str) -> None:
    try:
        job_store.set_status(doc_id, JobStatus.EXTRACTING_CLAUSES)
        clauses = await extract_clauses(doc_text)

        job_store.set_status(doc_id, JobStatus.SEARCHING_SOURCES)
        clauses_chunks = await retrieve_all_chunks(clauses)

        job_store.set_status(doc_id, JobStatus.GENERATING_RESPONSE)
        structured_input = build_analysis_context(clauses_chunks)
        final_analysis = await analyze_retrieved_clauses(structured_input)

        # Re-key matching_source_rules -> matching_clause_rules to match the
        # frontend's field name, without touching models/clause_model.py.
        results = []
        for item in final_analysis:
            data = item.model_dump()
            data["matching_clause_rules"] = data.pop("matching_source_rules")
            results.append(data)

        job_store.set_done(doc_id, results)
    except Exception as e:
        job_store.set_failed(doc_id, str(e))
