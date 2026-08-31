"""Feature derivation and inference wrapper for ANN compliance risk scoring."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np

from models.clause_model import ClauseAnalysis
from models.risk_ann_model import RISK_LABELS, RiskANN

MODEL_PATH = Path(__file__).resolve().parents[1] / "storage" / "models" / "risk_ann_demo.npz"


def derive_risk_features(
    analyses: list[ClauseAnalysis],
    verification_results: list[dict[str, Any]],
    historical_violation_count: int = 0,
) -> dict[str, float]:
    """Derive BRD feature inputs, each normalized to [0, 1]."""
    clause_count = max(len(analyses), 1)
    retrieval_confidence = sum(item.confidence for item in analyses) / clause_count
    regulatory_coverage = sum(bool(item.citations) for item in analyses) / clause_count
    clause_complexity = min(1.0, sum(len(item.clause_text.split()) for item in analyses) / (clause_count * 200))
    violations = sum(result["status"] == "FAIL" for result in verification_results)
    historical_violations = min(1.0, (historical_violation_count + violations) / 5)
    return {
        "retrieval_confidence": round(retrieval_confidence, 4),
        "historical_violation_count": round(historical_violations, 4),
        "clause_complexity": round(clause_complexity, 4),
        "regulatory_coverage": round(regulatory_coverage, 4),
    }


def score_document_risk(
    analyses: list[ClauseAnalysis],
    verification_results: list[dict[str, Any]],
    historical_violation_count: int = 0,
    model_path: str | Path = MODEL_PATH,
) -> dict[str, Any]:
    features = derive_risk_features(analyses, verification_results, historical_violation_count)
    path = Path(model_path)
    if not path.exists():
        return {"status": "unavailable", "message": "ANN model artifact is not available.", "features": features}
    probabilities = RiskANN.load(path).probabilities(np.array([[*features.values()]], dtype=float))[0]
    index = int(probabilities.argmax())
    return {
        "status": "complete",
        "model_type": "ANN 4-6-3 (demo-trained)",
        "risk_tier": RISK_LABELS[index],
        "confidence": round(float(probabilities[index]), 4),
        "probabilities": {label: round(float(value), 4) for label, value in zip(RISK_LABELS, probabilities)},
        "features": features,
        "explanation": "Risk tier is generated from retrieval confidence, deterministic/historical violations, clause complexity, and regulatory coverage.",
    }
