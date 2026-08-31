from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import json

from models.pipeline_status_model import PipelineStatus
from services.agent_orchestrator import ComplianceAgentOrchestrator, ComplianceWorkflowState
from services.document_controller import upload_user_document
from services.report_service import create_compliance_report, get_report_path, record_reviewer_decision

router = APIRouter(prefix="/upload-doc", tags=["user doc upload"])


class ReviewerDecisionRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=200)
    decision: str
    note: str | None = Field(default=None, max_length=2000)


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
    report_artifact = create_compliance_report(document_id, document_understanding, payload)
    payload["document_understanding"] = document_understanding
    payload["structured_entities"] = payload["entities"]
    payload["report"] = {"report_id": report_artifact["report_id"], "download_url": f"/upload-doc/reports/{report_artifact['report_id']}"}
    payload["stage"] = PipelineStatus.DONE
    yield f"data: {json.dumps(payload)}\n\n"


@router.get("/reports/{report_id}")
def download_compliance_report(report_id: str):
    try: path = get_report_path(report_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="Compliance report not found.") from exc
    return FileResponse(path, media_type="application/json", filename=path.name)


@router.post("/reports/{report_id}/review")
def submit_reviewer_decision(report_id: str, request: ReviewerDecisionRequest):
    try: return {"report_id": report_id, "review": record_reviewer_decision(report_id, request.reviewer_id, request.decision, request.note)}
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="Compliance report not found.") from exc
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/")
async def upload_document(file: UploadFile = File()):
    response = await upload_user_document(file)
    user_doc_text = response.pop("document_text")
    return StreamingResponse(run_pipeline(user_doc_text, response["document_understanding"], response["saved_doc_name"]), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

