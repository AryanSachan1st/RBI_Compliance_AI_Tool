from types import SimpleNamespace
import json

from services.report_service import create_compliance_report, get_report_path


def test_report_contains_required_brd_output_sections(tmp_path):
    payload = {
        "entities": {"overall_confidence": 0.9},
        "deterministic_verification": [{"rule_id": "EMI-001", "status": "PASS"}],
        "document_risk": {"risk_tier": "LOW"},
        "results": [{"clause_id": "C1", "verdict": "COMPLIANT", "citations": []}],
        "agent_trace": [{"agent": "reporting", "status": "complete"}],
    }
    result = create_compliance_report("doc-1", {"status": "complete"}, payload, tmp_path)
    report = json.loads(result["path"].read_text(encoding="utf-8"))
    assert report["document_risk"]["risk_tier"] == "LOW"
    assert report["clause_results"][0]["clause_id"] == "C1"
    assert get_report_path(result["report_id"], tmp_path) == result["path"]


def test_report_lookup_rejects_missing_or_wrong_extension(tmp_path):
    try:
        get_report_path("missing.pdf", tmp_path)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing report to be rejected")
