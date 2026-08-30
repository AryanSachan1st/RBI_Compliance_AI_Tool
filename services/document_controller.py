from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException

from services.document_parser import extract_text

UPLOAD_DIR = Path("storage/uploads")

async def upload_user_document(file: UploadFile):
    try:
        doc_id = str(uuid4())
        ext = Path(file.filename).suffix
        new_file_name= f"{doc_id}_{file.filename}{ext}"
        file_path = UPLOAD_DIR/new_file_name

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        with open(file_path, "wb") as store_file:
            store_file.write(await file.read())

        # Extract text to return
        content_pages = extract_text(file_path)
        total_pages = len(content_pages)
        total_words = 0
        for page in content_pages:
            total_words += len(page)

        return {
            "message": "Document uploaded successfully",
            "saved_doc_name": new_file_name,
            "original_file_name": file.filename,
            "total_pages": total_pages,
            "text_length": total_words
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )