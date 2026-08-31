"""Append-only audit connector for compliance pipeline events."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_AUDIT_LOG_PATH = Path(__file__).resolve().parents[1] / "storage" / "audit" / "events.jsonl"


def write_audit_event(
    event_type: str,
    document_id: str | None,
    payload: dict[str, Any],
    audit_log_path: str | Path = DEFAULT_AUDIT_LOG_PATH,
) -> dict[str, Any]:
    """Persist a JSONL audit event without storing raw uploaded document text."""
    event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "document_id": document_id,
        "payload": payload,
    }
    path = Path(audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    return event
