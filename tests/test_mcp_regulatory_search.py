from mcp_server import tools as mcp_tools


def test_regulatory_search_tool_returns_citation_and_audits(monkeypatch):
    events = []
    monkeypatch.setattr("services.audit_service.write_audit_event", lambda *args: events.append(args) or {"event_id": "1"})
    results = mcp_tools.search_regulatory_corpus(
        "APR disclosure",
        semantic_matches=[{
            "chunk_id": "rbi-apr", "text_content": "APR must be disclosed.",
            "source_title": "RBI Digital Lending Directions", "page_number": 4,
        }],
        document_id="doc-1",
    )
    assert results[0]["source_title"] == "RBI Digital Lending Directions"
    assert events[0][0] == "regulatory_search"
    assert events[0][1] == "doc-1"
