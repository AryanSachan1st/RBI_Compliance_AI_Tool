from services.evaluation_service import classification_metrics, entity_metrics, retrieval_metrics
def test_classification_metrics_reports_accuracy_and_per_class_scores():
    result = classification_metrics(["CLEAR", "FLAGGED"], ["CLEAR", "CLEAR"])
    assert result["accuracy"] == 0.5
    assert result["per_class"]["CLEAR"]["recall"] == 1.0
def test_retrieval_metrics_reports_rank_sensitive_scores():
    result = retrieval_metrics([{"relevant": ["a"], "returned": ["x", "a"]}], k=2)
    assert result["precision_at_k"] == 0.5
    assert result["mrr"] == 0.5
def test_entity_metrics_uses_entity_type_and_value():
    result = entity_metrics([{"entity_type": "emi", "value": "15000"}], [{"entity_type": "emi", "value": "15000"}])
    assert result["f1"] == 1.0
