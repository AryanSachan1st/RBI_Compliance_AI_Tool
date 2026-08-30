"""
pdf -> text
docx -> text
txt -> text
"""
from pathlib import Path
from PyPDF2 import PdfReader
from fastapi import HTTPException


def extract_pdf_text(file_path: str | Path) -> str:
    reader = PdfReader(str(file_path))

    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text

def extract_txt_text(file_path: str | Path) -> str:
    with open(file_path, "r") as file:
        content = file.read()

    return content

def extract_text(file_path: str | Path) -> str:
    file_path = Path(file_path)
    
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_pdf_text(file_path)
    elif ext == ".txt":
        return extract_txt_text(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .pdf and .txt allowed!"
        )