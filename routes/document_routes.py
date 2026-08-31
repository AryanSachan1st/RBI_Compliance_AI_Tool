from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
import json

from models.pipeline_status_model import PipelineStatus
from services.core_langchain_service import (
    analyze_retrieved_clauses,
    build_analysis_context,
    extract_clauses,
    extract_structured_entities,
    retrieve_all_chunks,
)
from services.document_controller import upload_user_document
from services.governance_service import apply_clause_confidence_gate
from services.verification_service import run_deterministic_verifications

router = APIRouter(prefix="/upload-doc", tags=["user doc upload"])


async def run_pipeline(doc_text: str, document_understanding: dict, document_id: str):
    yield f"data: {json.dumps({'stage': PipelineStatus.ANALYZING_DOCUMENT, 'document_understanding': document_understanding})}\n\n"

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_ENTITIES})}\n\n"
    entities = await extract_structured_entities(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.VERIFYING_FACTS})}\n\n"
    verification_results = run_deterministic_verifications(entities, document_id=document_id)

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"
    clauses = await extract_clauses(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    clauses_chunks = await retrieve_all_chunks(clauses)

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    final_analysis = await analyze_retrieved_clauses(build_analysis_context(clauses_chunks))
    governed_analysis = apply_clause_confidence_gate(final_analysis)
    serializable = [item.model_dump() for item in governed_analysis]

    payload = {
        "stage": PipelineStatus.DONE,
        "entities": entities.model_dump(),
        "deterministic_verification": verification_results,
        "results": serializable,
    }
    yield f"data: {json.dumps(payload)}\n\n"


@router.post("/")
async def upload_document(file: UploadFile = File()):
    response = await upload_user_document(file)
    user_doc_text = response.pop("document_text")
    return StreamingResponse(
        run_pipeline(user_doc_text, response["document_understanding"], response["saved_doc_name"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
