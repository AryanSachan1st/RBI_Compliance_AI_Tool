from fastapi import APIRouter, UploadFile, File
from services.document_controller import upload_user_document
from services.core_langchain_service import extract_clauses, retrieve_all_chunks, build_analysis_context, analyze_retrieved_clauses
import json, asyncio
from fastapi.responses import StreamingResponse
from models.pipeline_status_model import PipelineStatus

router = APIRouter(
    prefix="/upload-doc",
    tags=["user doc upload"]
)

async def run_pipeline(doc_text: str):
    # Stage 1
    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"
    clauses = await extract_clauses(doc_text)

    # Stage 2
    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    clauses_chunks = await retrieve_all_chunks(clauses)

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    structured_input = build_analysis_context(clauses_chunks)
    final_analysis = await analyze_retrieved_clauses(structured_input)

    yield f"data: {json.dumps({'stage': PipelineStatus.DONE, 'results': final_analysis})}"

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