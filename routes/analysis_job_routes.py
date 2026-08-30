"""
Job-based document analysis API, built to match the frontend's expected
contract (src/api/documents.ts, src/hooks/useDocumentStatus.ts) exactly:

    POST /documents/                -> create a job, returns immediately
    GET  /documents/{doc_id}/status -> poll job status
    GET  /documents/{doc_id}/report -> fetch final results once DONE
    GET  /documents/{doc_id}/stream -> live SSE push (GET-based, so the
                                        browser's EventSource can use it)

This intentionally duplicates some logic already in routes/document_routes.py
and services/document_controller.py rather than modifying either - the
original synchronous /upload-doc/ endpoint is left completely untouched.
"""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from models.job_models import JobReportResponse, JobStatusResponse, UploadJobResponse
from models.job_status_model import JobStatus
from services import job_store
from services.analysis_job_runner import run_analysis_job
from services.document_parser import extract_text

router = APIRouter(
    prefix="/documents",
    tags=["async document analysis"],
)

UPLOAD_DIR = Path("storage/uploads")


@router.post("/", response_model=UploadJobResponse)
async def create_analysis_job(file: UploadFile | None = None):
    if not file:
        file = File()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    ext = Path(file.filename).suffix
    if ext.lower() not in (".pdf", ".txt", ".docx"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .pdf, .docx and .txt allowed!",
        )

    doc_id = str(uuid4())
    saved_name = f"{doc_id}{ext}"
    file_path = UPLOAD_DIR / saved_name

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as out:
        out.write(await file.read())

    doc_text = extract_text(file_path)

    job_store.create_job(doc_id, original_file_name=file.filename)

    # Fire-and-forget: the request returns immediately, the pipeline keeps
    # running and reports progress into job_store.
    asyncio.create_task(run_analysis_job(doc_id, doc_text))

    return UploadJobResponse(doc_id=doc_id, status=JobStatus.QUEUED)


@router.get("/{doc_id}/status", response_model=JobStatusResponse)
async def get_job_status(doc_id: str):
    job = job_store.get_job(doc_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such document job.")

    return JobStatusResponse(
        doc_id=job.doc_id,
        status=job.status,
        original_file_name=job.original_file_name,
        error=job.error,
    )


@router.get("/{doc_id}/report", response_model=JobReportResponse)
async def get_job_report(doc_id: str):
    job = job_store.get_job(doc_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such document job.")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=409, detail="This document is still being processed."
        )

    return JobReportResponse(doc_id=job.doc_id, results=job.results or [])


@router.get("/{doc_id}/stream")
async def stream_job_status(doc_id: str):
    job = job_store.get_job(doc_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such document job.")

    async def event_source():
        # Send whatever the current status already is before waiting on
        # anything new - covers the case where the job reached a terminal
        # state between the initial GET /status call and opening the stream.
        current = job_store.get_job(doc_id)
        if current is None:
            return

        yield f"data: {json.dumps({'status': current.status.value})}\n\n"
        if current.status in (JobStatus.DONE, JobStatus.FAILED):
            payload = {"status": current.status.value}
            if current.status == JobStatus.DONE:
                payload["results"] = current.results
            else:
                payload["error"] = current.error
            yield f"data: {json.dumps(payload)}\n\n"
            return

        queue = job_store.subscribe(doc_id)
        if queue is None:
            return
        try:
            while True:
                status = await queue.get()
                current = job_store.get_job(doc_id)
                if current is None:
                    return

                if status == JobStatus.DONE:
                    yield f"data: {json.dumps({'status': status.value, 'results': current.results})}\n\n"
                    return
                if status == JobStatus.FAILED:
                    yield f"data: {json.dumps({'status': status.value, 'error': current.error})}\n\n"
                    return

                yield f"data: {json.dumps({'status': status.value})}\n\n"
        finally:
            job_store.unsubscribe(doc_id, queue)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
