from models.clause_model import ClauseAnalysis, RegulatoryCitation
from rule_engine.config import RuleEngineConfig
from services.governance_service import apply_clause_confidence_gate


def _analysis(**overrides):
    base = {
        "clause_id": "C1",
        "clause_type": "Interest",
        "clause_text": "Interest rate is 12%.",
        "analysis": "The clause is aligned with the cited provision.",
        "risk": "LOW",
        "recommendation": "No change needed.",
        "verdict": "COMPLIANT",
        "confidence": 0.95,
        "citations": [RegulatoryCitation(source_title="RBI Directions", page_number=4, excerpt="Disclose the annual rate.")],
    }
    base.update(overrides)
    return ClauseAnalysis(**base)


def test_gate_keeps_cited_high_confidence_verdict():
    result = apply_clause_confidence_gate([_analysis()])
    assert result[0].verdict == "COMPLIANT"


def test_low_confidence_forces_manual_review():
    result = apply_clause_confidence_gate([_analysis(confidence=0.5)])
    assert result[0].verdict == "UNCERTAIN_MANUAL_REVIEW"
    assert "confidence" in result[0].recommendation


def test_missing_citation_forces_manual_review():
    result = apply_clause_confidence_gate([_analysis(citations=[])])
    assert result[0].verdict == "UNCERTAIN_MANUAL_REVIEW"
    assert "citation" in result[0].recommendation


def test_threshold_is_configurable():
    result = apply_clause_confidence_gate([_analysis(confidence=0.7)], RuleEngineConfig(confidence_threshold=0.6))
    assert result[0].verdict == "COMPLIANT"
