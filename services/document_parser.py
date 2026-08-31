"""Text extraction for digital PDFs and OCR-backed scanned documents/images."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import HTTPException
from PyPDF2 import PdfReader

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_EXTENSIONS = {".pdf", ".txt", *IMAGE_EXTENSIONS}


def _ocr_images(images: Iterable[object]) -> str:
    """OCR PIL images, raising a useful API error when Tesseract is unavailable."""
    try:
        import pytesseract
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="OCR support is unavailable. Install pytesseract and the Tesseract OCR engine.",
        ) from exc
    try:
        pages = [pytesseract.image_to_string(image) for image in images]
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Tesseract OCR engine was not found. Install Tesseract and add it to PATH.",
        ) from exc
    return "\f".join(page for page in pages if page)


def extract_pdf_text(file_path: str | Path) -> str:
    """Read digital PDF text, OCRing only pages without an embedded text layer."""
    path = Path(file_path)
    reader = PdfReader(str(path))
    page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    missing_pages = [index for index, text in enumerate(page_text) if not text]
    if not missing_pages:
        return "\f".join(page_text)

    try:
        import fitz
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Scanned-PDF OCR requires PyMuPDF, Pillow, pytesseract, and Tesseract.",
        ) from exc

    document = fitz.open(path)
    try:
        images = []
        for index in missing_pages:
            pixmap = document.load_page(index).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            images.append(Image.open(__import__("io").BytesIO(pixmap.tobytes("png"))))
        ocr_pages = _ocr_images(images).split("\f")
    finally:
        document.close()

    for index, text in zip(missing_pages, ocr_pages):
        page_text[index] = text.strip()
    return "\f".join(page_text)


def extract_image_text(file_path: str | Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Image OCR requires Pillow, pytesseract, and Tesseract.") from exc
    with Image.open(file_path) as image:
        return _ocr_images([image.copy()])


def extract_txt_text(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def extract_text(file_path: str | Path) -> str:
    """Extract text from a PDF/TXT or OCR text from a PNG/JPEG document image."""
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(path)
    if ext == ".txt":
        return extract_txt_text(path)
    if ext in IMAGE_EXTENSIONS:
        return extract_image_text(path)
    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Allowed types: PDF, TXT, PNG, JPG, JPEG.",
    )
