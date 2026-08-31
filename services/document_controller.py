from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException

from services.document_parser import extract_text
from services.document_understanding import analyze_document

UPLOAD_DIR = Path("storage/uploads")

async def upload_user_document(file: UploadFile):
    try:
        doc_id = str(uuid4())
        ext = Path(file.filename).suffix
        new_file_name= f"{doc_id}_{Path(file.filename).stem}{ext}"
        file_path = UPLOAD_DIR/new_file_name

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        with open(file_path, "wb") as store_file:
            store_file.write(await file.read())

        # Extract text to return
        document_text = extract_text(file_path)
        total_pages = len(document_text.split("\f"))
        total_words = len(document_text.split())
        document_understanding = analyze_document(file_path)

        return {
            "message": "Document uploaded successfully",
            "saved_doc_name": new_file_name,
            "original_file_name": file.filename,
            "total_pages": total_pages,
            "text_length": len(document_text),
            "total_words": total_words,
            "document_understanding": document_understanding,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

