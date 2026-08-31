"""Generate, review, and serve traceable compliance-report artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

REPORT_DIRECTORY = Path(__file__).resolve().parents[1] / "storage" / "reports"
REVIEW_DECISIONS = frozenset({"APPROVED", "REJECTED", "ESCALATED"})


def _safe_report_name(document_id: str) -> str:
    return "".join(character for character in document_id if character.isalnum() or character in {"-", "_"})


def create_compliance_report(document_id: str, document_understanding: dict[str, Any], workflow_payload: dict[str, Any], report_directory: str | Path = REPORT_DIRECTORY) -> dict[str, Any]:
    """Write a JSON report with evidence, outcomes, and audit-agent trace."""
    report = {"report_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "document_id": document_id, "document_understanding": document_understanding, "structured_entities": workflow_payload["entities"], "deterministic_verification": workflow_payload["deterministic_verification"], "document_risk": workflow_payload["document_risk"], "clause_results": workflow_payload["results"], "agent_trace": workflow_payload["agent_trace"], "reviewer_decision": None, "reviewer_note": None}
    directory = Path(report_directory); directory.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_report_name(document_id)}_compliance_report.json"; path = directory / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"report_id": filename, "path": path, "report": report}


def get_report_path(report_id: str, report_directory: str | Path = REPORT_DIRECTORY) -> Path:
    safe_id = _safe_report_name(Path(report_id).stem) + Path(report_id).suffix; path = Path(report_directory) / safe_id
    if not path.exists() or path.suffix != ".json": raise FileNotFoundError(report_id)
    return path


def record_reviewer_decision(report_id: str, reviewer_id: str, decision: str, note: str | None = None, report_directory: str | Path = REPORT_DIRECTORY) -> dict[str, Any]:
    """Persist a required human decision without changing the generated evidence."""
    normalized_decision = decision.strip().upper()
    if normalized_decision not in REVIEW_DECISIONS: raise ValueError(f"Decision must be one of: {', '.join(sorted(REVIEW_DECISIONS))}.")
    if not reviewer_id.strip(): raise ValueError("reviewer_id is required.")
    path = get_report_path(report_id, report_directory)
    report = json.loads(path.read_text(encoding="utf-8"))
    review = {"decision": normalized_decision, "reviewer_id": reviewer_id.strip(), "note": note.strip() if note else None, "decided_at": datetime.now(timezone.utc).isoformat()}
    report["reviewer_decision"] = review; report["reviewer_note"] = review["note"]
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    from services.audit_service import write_audit_event
    write_audit_event("reviewer_decision", report.get("document_id"), {"report_id": report_id, **review})
    return review
