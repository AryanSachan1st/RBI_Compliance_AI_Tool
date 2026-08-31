import json
import pytest
from services.report_service import create_compliance_report, record_reviewer_decision

def payload():
    return {"entities": {}, "deterministic_verification": [], "document_risk": {}, "results": [], "agent_trace": []}

def test_reviewer_decision_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr("services.audit_service.DEFAULT_AUDIT_LOG_PATH", tmp_path / "audit.jsonl")
    report = create_compliance_report("doc-1", {}, payload(), tmp_path)
    decision = record_reviewer_decision(report["report_id"], "reviewer@example.com", "approved", "Looks good", tmp_path)
    saved = json.loads(report["path"].read_text(encoding="utf-8"))
    assert decision["decision"] == "APPROVED"
    assert saved["reviewer_decision"]["reviewer_id"] == "reviewer@example.com"
    assert saved["reviewer_note"] == "Looks good"

def test_reviewer_decision_rejects_unknown_status(tmp_path):
    report = create_compliance_report("doc-1", {}, payload(), tmp_path)
    with pytest.raises(ValueError, match="Decision must be"):
        record_reviewer_decision(report["report_id"], "reviewer", "pending", report_directory=tmp_path)
