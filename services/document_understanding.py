"""Visual document-understanding checks with an optional trained CNN classifier."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

MODEL_PATH = Path("models/authenticity_model.h5")
CLASS_NAMES = ["Loan_Agreement", "Insurance_Policy", "KYC_Form", "Other"]
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
PAGE_NUMBER_PATTERN = re.compile(r"\b(?:page\s*)?(\d{1,3})\s*(?:of|/)\s*(\d{1,3})\b", re.IGNORECASE)


def _quality_label(blur_score: float) -> str:
    if blur_score > 100: return "Good"
    if blur_score > 50: return "Average"
    return "Poor"


def _page_sequence(texts: list[str]) -> dict[str, Any]:
    declared: list[int] = []
    totals: list[int] = []
    for text in texts:
        match = PAGE_NUMBER_PATTERN.search(text)
        if match:
            declared.append(int(match.group(1))); totals.append(int(match.group(2)))
    expected_total = max(totals, default=0)
    missing = sorted(set(range(1, expected_total + 1)) - set(declared)) if expected_total else []
    return {"declared_page_numbers": declared, "declared_total_pages": expected_total or None, "missing_page_numbers": missing, "page_sequence_status": "INCOMPLETE" if missing else ("VERIFIED" if declared else "NOT_DECLARED")}


def _signature_present(gray: Any, cv2: Any) -> bool:
    """Conservative visual indicator, never proof of signature authenticity."""
    height, width = gray.shape[:2]
    region = gray[int(height * 0.62):height, :]
    edges = cv2.Canny(region, 100, 200)
    return bool(cv2.countNonZero(edges) > max(600, width * 3))


def analyze_document(file_path: str | Path) -> dict[str, Any]:
    """Assess visual quality/layout even when the optional CNN model is unavailable."""
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"status": "not_supported", "message": "Document understanding accepts PDF, PNG, JPG, and JPEG files.", "pages": []}
    try:
        import cv2
        import fitz
        import numpy as np
    except ImportError:
        return {"status": "unavailable", "message": "Visual-analysis dependencies are not installed. Install PyMuPDF and opencv-python-headless.", "pages": []}

    model = None
    model_message = None
    if MODEL_PATH.exists():
        try:
            import tensorflow as tf
            model = tf.keras.models.load_model(MODEL_PATH)
        except (ImportError, OSError, ValueError) as exc:
            model_message = f"CNN classification unavailable: {exc}"
    else:
        model_message = f"CNN model artifact not found at {MODEL_PATH}."

    pdf = None
    try:
        page_texts: list[str] = []
        if path.suffix.lower() == ".pdf":
            pdf = fitz.open(path)
            page_images = []
            for page in pdf:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                image = cv2.imdecode(np.frombuffer(pixmap.tobytes("png"), dtype=np.uint8), cv2.IMREAD_COLOR)
                page_images.append(image); page_texts.append(page.get_text())
        else:
            page_images = [cv2.imread(str(path))]; page_texts = [""]
        if any(image is None for image in page_images): raise ValueError("Unable to decode uploaded document image.")

        pages: list[dict[str, Any]] = []
        for page_number, image in enumerate(page_images, start=1):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            height, width = image.shape[:2]
            item = {"page_number": page_number, "scan_quality": _quality_label(blur_score), "blur_score": round(blur_score, 2), "signature_present": _signature_present(gray, cv2), "layout": "LANDSCAPE" if width > height else "PORTRAIT", "image_dimensions": {"width": width, "height": height}, "document_type": "UNAVAILABLE", "classification_confidence": None}
            if model is not None:
                prediction = model.predict(cv2.resize(image, (224, 224)).astype("float32")[None, ...], verbose=0)[0]
                index = int(prediction.argmax())
                item.update({"document_type": CLASS_NAMES[index], "classification_confidence": round(float(prediction[index]), 4)})
            pages.append(item)
        sequence = _page_sequence(page_texts)
        status = "complete" if model is not None else "partial"
        return {"status": status, "message": "CNN and visual analysis complete." if model is not None else "Visual checks complete; CNN classification is unavailable until a trained model is installed.", "cnn_classifier": {"available": model is not None, "model_path": str(MODEL_PATH), "reason": model_message}, "page_count": len(pages), **sequence, "pages": pages}
    except Exception as exc:
        return {"status": "failed", "message": f"Document-understanding analysis failed: {exc}", "pages": []}
    finally:
        if pdf is not None: pdf.close()
