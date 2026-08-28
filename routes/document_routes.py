from fastapi import APIRouter, UploadFile, File
from services.document_controller import upload_user_document
from services.document_parser import extract_text
from services.core_langchain_service import extract_clauses, retrieve_all_chunks, build_analysis_context, analyze_retrieved_clauses

router = APIRouter(
    prefix="/upload-doc",
    tags=["user doc upload"]
)


@router.post("/")
async def upload_document(file: UploadFile = File()):
    response = await upload_user_document(file)

    user_doc_text = extract_text(response["file_path"])
    user_doc_clauses = extract_clauses(user_doc_text)
    all_clauses_chunks = retrieve_all_chunks(user_doc_clauses)
    structured_user_input = build_analysis_context(all_clauses_chunks)
    final_analysis = analyze_retrieved_clauses(structured_user_input)

    return final_analysis