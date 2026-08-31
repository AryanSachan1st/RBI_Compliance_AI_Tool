"""Deterministic, dependency-free metrics for BRD component evaluation."""
from __future__ import annotations
from typing import Any

def classification_metrics(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    if len(expected) != len(predicted): raise ValueError("Expected and predicted result counts must match.")
    if not expected: raise ValueError("At least one labelled result is required.")
    labels = sorted(set(expected) | set(predicted))
    confusion = {label: {other: 0 for other in labels} for label in labels}
    for actual, result in zip(expected, predicted): confusion[actual][result] += 1
    per_class = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[actual][label] for actual in labels if actual != label)
        fn = sum(confusion[label][result] for result in labels if result != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": sum(confusion[label].values()), "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    correct = sum(actual == result for actual, result in zip(expected, predicted))
    return {"sample_count": len(expected), "accuracy": round(correct / len(expected), 4), "per_class": per_class, "confusion_matrix": confusion}

def retrieval_metrics(rows: list[dict[str, Any]], k: int = 3) -> dict[str, Any]:
    if not rows: raise ValueError("At least one retrieval evaluation row is required.")
    if k < 1: raise ValueError("k must be at least 1.")
    precisions, recalls, reciprocal_ranks = [], [], []
    for row in rows:
        relevant = set(row.get("relevant", [])); returned = row.get("returned", [])[:k]
        hits = sum(item in relevant for item in returned)
        precisions.append(hits / k); recalls.append(hits / len(relevant) if relevant else 1.0)
        rank = next((index for index, item in enumerate(returned, 1) if item in relevant), None)
        reciprocal_ranks.append(1 / rank if rank else 0.0)
    return {"sample_count": len(rows), "k": k, "precision_at_k": round(sum(precisions) / len(rows), 4), "recall_at_k": round(sum(recalls) / len(rows), 4), "mrr": round(sum(reciprocal_ranks) / len(rows), 4)}

def entity_metrics(expected: list[dict[str, str]], predicted: list[dict[str, str]]) -> dict[str, Any]:
    expected_set = {(item["entity_type"], item["value"]) for item in expected}; predicted_set = {(item["entity_type"], item["value"]) for item in predicted}
    tp = len(expected_set & predicted_set); precision = tp / len(predicted_set) if predicted_set else 0.0; recall = tp / len(expected_set) if expected_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"expected_count": len(expected_set), "predicted_count": len(predicted_set), "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
