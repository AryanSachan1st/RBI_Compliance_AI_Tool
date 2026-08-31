from models.clause_model import ClauseAnalysis, RegulatoryCitation
from services.risk_scoring_service import derive_risk_features, score_document_risk


def _analysis(confidence=0.9, citation=True):
    return ClauseAnalysis(
        clause_id="C1", clause_type="Fees", clause_text="A short clause with a fee disclosure.",
        analysis="Supported by source.", risk="LOW", recommendation="None.", verdict="COMPLIANT",
        confidence=confidence,
        citations=[RegulatoryCitation(source_title="RBI Directions", excerpt="Disclose fees.")] if citation else [],
    )


def test_features_are_traceable_and_normalized():
    features = derive_risk_features([_analysis()], [{"status": "FAIL"}], historical_violation_count=1)
    assert features["retrieval_confidence"] == 0.9
    assert features["regulatory_coverage"] == 1.0
    assert features["historical_violation_count"] == 0.4


def test_ann_returns_a_document_risk_tier():
    result = score_document_risk([_analysis()], [{"status": "PASS"}])
    assert result["status"] == "complete"
    assert result["risk_tier"] in {"LOW", "MEDIUM", "HIGH"}
    assert set(result["probabilities"]) == {"LOW", "MEDIUM", "HIGH"}


def test_missing_model_is_explicit_not_fabricated(tmp_path):
    result = score_document_risk([_analysis()], [], model_path=tmp_path / "missing.npz")
    assert result["status"] == "unavailable"
