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

router = APIRouter(prefix="/upload-doc", tags=["user doc upload"])


async def run_pipeline(doc_text: str, document_understanding: dict):
    yield f"data: {json.dumps({'stage': PipelineStatus.ANALYZING_DOCUMENT, 'document_understanding': document_understanding})}\n\n"

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_ENTITIES})}\n\n"
    entities = await extract_structured_entities(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"
    clauses = await extract_clauses(doc_text)

    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    clauses_chunks = await retrieve_all_chunks(clauses)

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    final_analysis = await analyze_retrieved_clauses(build_analysis_context(clauses_chunks))
    serializable = [item.model_dump() for item in final_analysis]

    yield f"data: {json.dumps({'stage': PipelineStatus.DONE, 'entities': entities.model_dump(), 'results': serializable})}\n\n"


@router.post("/")
async def upload_document(file: UploadFile = File()):
    response = await upload_user_document(file)
    user_doc_text = response.pop("document_text")
    return StreamingResponse(
        run_pipeline(user_doc_text, response["document_understanding"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
