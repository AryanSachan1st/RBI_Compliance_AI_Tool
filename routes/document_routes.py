from fastapi import APIRouter, UploadFile, File
from services.document_controller import upload_user_document
from services.core_langchain_service import extract_clauses, retrieve_all_chunks, build_analysis_context, analyze_retrieved_clauses
import json, asyncio
from fastapi.responses import StreamingResponse
from models.pipeline_status_model import PipelineStatus

# --- Added for Rule Engine integration (does not change anything above) ---
from services.numeric_extraction_service import extract_loan_numerics
from services.rule_validation_service import run_rule_validations
# --- end addition ---

router = APIRouter(
    prefix="/upload-doc",
    tags=["user doc upload"]
)

async def run_pipeline(doc_text: str):
    # Stage 1
    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"
    clauses = extract_clauses(doc_text)

    # Stage 2
    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    clauses_chunks = await retrieve_all_chunks(clauses)

    # --- Added for Rule Engine integration (new stage, existing stages/calls above and below are unchanged) ---
    # Independent extraction pass over the same raw doc_text (not derived
    # from `clauses` above) to pull out the structured numbers rule_engine/
    # needs, then run the deterministic checks against them. If this step
    # errors for any reason, the original clause-analysis flow below still
    # runs -- a rule-validation failure must never block the existing,
    # already-working pipeline.
    yield f"data: {json.dumps({'stage': PipelineStatus.VALIDATING_RULES})}\n\n"
    extracted_numerics_json = None
    try:
        extracted_numerics = extract_loan_numerics(doc_text)
        extracted_numerics_json = extracted_numerics.model_dump()
        rule_validations = run_rule_validations(extracted_numerics)
    except Exception as exc:
        rule_validations = [{
            "rule_id": "ALL",
            "skipped": True,
            "reason": f"Numeric extraction/validation step failed: {exc}",
        }]
    # --- end addition ---

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    structured_input = build_analysis_context(clauses_chunks)
    final_analysis = analyze_retrieved_clauses(structured_input)
    final_analysis_json = [item.model_dump() for item in final_analysis]
    yield f"data: {json.dumps({'stage': PipelineStatus.DONE, 'results': final_analysis_json, 'rule_validations': rule_validations, 'extracted_numerics': extracted_numerics_json})}"

@router.post("/")
async def upload_document(file: UploadFile = File()):
    response = await upload_user_document(file)
    user_doc_text = response["content"]

    return StreamingResponse(
        run_pipeline(user_doc_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )