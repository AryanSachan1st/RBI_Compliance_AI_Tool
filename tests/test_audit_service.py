import json

from services.audit_service import write_audit_event


def test_audit_event_is_append_only_and_json_safe(tmp_path):
    path = tmp_path / "events.jsonl"
    first = write_audit_event("calculator_used", "doc-1", {"status": "PASS"}, path)
    second = write_audit_event("retrieval_used", "doc-1", {"source_titles": ["RBI Directions"]}, path)
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [line["event_id"] for line in lines] == [first["event_id"], second["event_id"]]
    assert lines[1]["payload"]["source_titles"] == ["RBI Directions"]
