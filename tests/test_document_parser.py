from fastapi import HTTPException
import pytest

from services import document_parser


def test_extract_text_routes_pdf_to_pdf_parser(monkeypatch):
    monkeypatch.setattr(document_parser, "extract_pdf_text", lambda _: "digital text")
    assert document_parser.extract_text("agreement.pdf") == "digital text"


def test_extract_text_routes_images_to_ocr(monkeypatch):
    monkeypatch.setattr(document_parser, "extract_image_text", lambda _: "ocr text")
    assert document_parser.extract_text("scan.JPG") == "ocr text"
    assert document_parser.extract_text("photo.png") == "ocr text"


def test_extract_text_rejects_unsupported_files():
    with pytest.raises(HTTPException) as exc_info:
        document_parser.extract_text("agreement.docx")
    assert exc_info.value.status_code == 400


def test_ocr_reports_missing_python_dependency(monkeypatch):
    import builtins
    original_import = builtins.__import__

    def block_pytesseract(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_pytesseract)
    with pytest.raises(HTTPException) as exc_info:
        document_parser._ocr_images([object()])
    assert exc_info.value.status_code == 503
