from services.document_understanding import _page_sequence

def test_page_sequence_detects_missing_declared_page():
    result = _page_sequence(["Page 1 of 3", "Page 3 of 3"])
    assert result["missing_page_numbers"] == [2]
    assert result["page_sequence_status"] == "INCOMPLETE"

def test_page_sequence_is_not_declared_without_page_labels():
    result = _page_sequence(["Loan agreement", "Terms and conditions"])
    assert result["page_sequence_status"] == "NOT_DECLARED"
    assert result["missing_page_numbers"] == []


def test_classifier_uses_saved_label_contract(tmp_path, monkeypatch):
    labels_path = tmp_path / "labels.json"
    labels_path.write_text('["Loan", "Insurance", "KYC", "Other"]', encoding="utf-8")
    monkeypatch.setattr("services.document_understanding.LABELS_PATH", labels_path)
    from services.document_understanding import _class_names
    assert _class_names() == ["Loan", "Insurance", "KYC", "Other"]
