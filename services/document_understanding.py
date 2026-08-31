"""CNN-backed visual checks for uploaded documents."""
from __future__ import annotations

from pathlib import Path
from typing import Any

MODEL_PATH = Path("models/authenticity_model.h5")
CLASS_NAMES = ["Loan_Agreement", "Insurance_Policy", "KYC_Form", "Other"]
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def _quality_label(blur_score: float) -> str:
    if blur_score > 100:
        return "Good"
    if blur_score > 50:
        return "Average"
    return "Poor"


def analyze_document(file_path: str | Path) -> dict[str, Any]:
    """Run visual quality, signature, and CNN type checks over PDF pages or images."""
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"status": "not_supported", "message": "CNN document understanding accepts PDF, PNG, JPG, and JPEG files.", "pages": []}
    try:
        import cv2
        import fitz
        import numpy as np
        import tensorflow as tf
    except ImportError:
        return {"status": "unavailable", "message": "CNN dependencies are not installed. Install PyMuPDF, opencv-python-headless, and tensorflow.", "pages": []}
    if not MODEL_PATH.exists():
        return {"status": "unavailable", "message": f"CNN model artifact not found at {MODEL_PATH}.", "pages": []}
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        pdf = None
        if path.suffix.lower() == ".pdf":
            pdf = fitz.open(path)
            page_images = [
                cv2.imdecode(
                    np.frombuffer(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png"), dtype=np.uint8),
                    cv2.IMREAD_COLOR,
                )
                for page in pdf
            ]
        else:
            page_images = [cv2.imread(str(path))]
        if any(image is None for image in page_images):
            raise ValueError("Unable to decode uploaded document image.")

        pages: list[dict[str, Any]] = []
        for page_number, image in enumerate(page_images, start=1):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            signature_present = bool(cv2.countNonZero(cv2.Canny(gray, 100, 200)) > 5000)
            prediction = model.predict(cv2.resize(image, (224, 224)).astype("float32")[None, ...], verbose=0)[0]
            class_index = int(prediction.argmax())
            pages.append({
                "page_number": page_number,
                "document_type": CLASS_NAMES[class_index],
                "classification_confidence": round(float(prediction[class_index]), 4),
                "scan_quality": _quality_label(blur_score),
                "blur_score": round(blur_score, 2),
                "signature_present": signature_present,
            })
        return {"status": "complete", "message": "CNN analysis complete.", "pages": pages}
    except Exception as exc:
        return {"status": "failed", "message": f"CNN analysis failed: {exc}", "pages": []}
    finally:
        if 'pdf' in locals() and pdf is not None:
            pdf.close()
