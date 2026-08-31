from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
import json

from models.pipeline_status_model import PipelineStatus
from services.agent_orchestrator import ComplianceAgentOrchestrator, ComplianceWorkflowState
from services.document_controller import upload_user_document

router = APIRouter(prefix="/upload-doc", tags=["user doc upload"])


async def run_pipeline(doc_text: str, document_understanding: dict, document_id: str):
    agents = ComplianceAgentOrchestrator()
    state = ComplianceWorkflowState(document_id, document_understanding)
    yield f"data: {json.dumps({'stage': PipelineStatus.ANALYZING_DOCUMENT, 'document_understanding': document_understanding})}\n\n"

    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_ENTITIES})}\n\n"
    await agents.document_analysis_agent(state, doc_text)
    yield f"data: {json.dumps({'stage': PipelineStatus.EXTRACTING_CLAUSES})}\n\n"

    yield f"data: {json.dumps({'stage': PipelineStatus.VERIFYING_FACTS})}\n\n"
    agents.numerical_verification_agent(state)

    yield f"data: {json.dumps({'stage': PipelineStatus.SEARCHING_SOURCES})}\n\n"
    await agents.regulatory_retrieval_agent(state)

    yield f"data: {json.dumps({'stage': PipelineStatus.GENERATING_RESPONSE})}\n\n"
    await agents.compliance_reasoning_agent(state)

    yield f"data: {json.dumps({'stage': PipelineStatus.SCORING_RISK})}\n\n"
    agents.risk_assessment_agent(state)
    payload = agents.reporting_agent(state)
    payload["stage"] = PipelineStatus.DONE
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
