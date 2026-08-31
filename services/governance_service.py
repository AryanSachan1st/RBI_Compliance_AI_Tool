"""Governance controls for clause-level AI compliance verdicts."""
from __future__ import annotations

from models.clause_model import ClauseAnalysis
from rule_engine.config import RuleEngineConfig


def apply_clause_confidence_gate(
    analyses: list[ClauseAnalysis],
    config: RuleEngineConfig | None = None,
) -> list[ClauseAnalysis]:
    """Enforce BR-01 and BR-04 before clause verdicts leave the pipeline.

    A clause is never presented as compliant/non-compliant if the LLM's
    confidence is below the configured threshold or it lacks a regulatory
    citation. Both conditions force manual review.
    """
    threshold = (config or RuleEngineConfig()).confidence_threshold
    governed: list[ClauseAnalysis] = []
    for analysis in analyses:
        reasons: list[str] = []
        if analysis.confidence < threshold:
            reasons.append(f"confidence {analysis.confidence:.2f} is below {threshold:.2f}")
        if not analysis.citations:
            reasons.append("no regulatory citation was supplied")
        if reasons:
            suffix = "Manual review required because " + " and ".join(reasons) + "."
            governed.append(analysis.model_copy(update={
                "verdict": "UNCERTAIN_MANUAL_REVIEW",
                "recommendation": f"{analysis.recommendation} {suffix}".strip(),
            }))
        else:
            governed.append(analysis)
    return governed
