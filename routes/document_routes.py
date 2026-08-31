from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
import json

from mcp_server.tools import log_audit_event
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
from services.risk_scoring_service import score_document_risk
from services.verification_service import run_deterministic_verifications

router = APIRouter(prefix="/upload-doc", tags=["user doc upload"])


async def run_pipeline(doc_text: str, document_understanding: dict, document_id: str):
    yield f"data: {json.dumps({'stage': PipelineStatus.ANALYZING_DOCUMENT, 'document_understanding': document_understanding})}\n\n"

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_ENTITIES})}\n\n"
    entities = await extract_structured_entities(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.VERIFYING_FACTS})}\n\n"
    verification_results = run_deterministic_verifications(entities, document_id=document_id)
    log_audit_event("calculator_used", document_id, {"rule_results": verification_results})

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"
    clauses = await extract_clauses(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    clauses_chunks = await retrieve_all_chunks(clauses)
    log_audit_event("regulatory_retrieval_used", document_id, {
        "clause_count": len(clauses_chunks),
        "citations": [
            {"clause_id": clause["clause_id"], "source_title": item.get("source_title"), "page_number": item.get("page_number")}
            for clause in clauses_chunks for item in clause["relevant_source_chunks"]
        ],
    })

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    final_analysis = await analyze_retrieved_clauses(build_analysis_context(clauses_chunks))
    governed_analysis = apply_clause_confidence_gate(final_analysis)

    yield f"data: {json.dumps({'stage': PipelineStatus.SCORING_RISK})}\n\n"
    document_risk = score_document_risk(governed_analysis, verification_results)
    serializable = [item.model_dump() for item in governed_analysis]
    log_audit_event("compliance_decision_generated", document_id, {
        "document_risk": document_risk,
        "clause_verdicts": [{"clause_id": item.clause_id, "verdict": item.verdict, "confidence": item.confidence} for item in governed_analysis],
    })

    payload = {
        "stage": PipelineStatus.DONE,
        "entities": entities.model_dump(),
        "deterministic_verification": verification_results,
        "document_risk": document_risk,
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
