"""
rule_engine/rules/interest.py

INTEREST-001: Interest Rate Validation.

Checks the annual interest rate stated in a document against a configured
maximum permissible rate (Section 8). Same shape as EMI-001 — confidence
gate first, then a deterministic comparison — but the comparison itself
goes through the shared `threshold` module (Section 9) instead of being
re-implemented here, since "is X over a configured limit" is not unique
to interest rates.

IMPORTANT — placeholder threshold, not a real regulatory ceiling: see the
`max_interest_rate` docstring in rule_engine/config.py. This is NOT an
actual RBI-mandated cap; it must be replaced once sourced from the team's
real regulatory data.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from rule_engine.base import Rule
from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.result import RuleResult
from rule_engine.threshold import ComparisonDirection, compare_against_threshold


class InterestRateValidationInput(BaseModel):
    """Typed, validated inputs for INTEREST-001."""

    document_interest_rate: Decimal = Field(
        ..., description="Annual interest rate as stated in the document, e.g. 14 for 14%."
    )

    @field_validator("document_interest_rate")
    @classmethod
    def _rate_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("interest rate cannot be negative")
        return v


class InterestRateValidationRule(Rule[InterestRateValidationInput]):
    rule_id = "INTEREST-001"
    rule_name = "Interest Rate Validation"
    rule_version = "1.0.0"

    def evaluate(
        self,
        inputs: InterestRateValidationInput,
        context: RuleContext,
        config: RuleEngineConfig,
    ) -> RuleResult:
        # 1. Confidence gate (BR-01) — checked before anything else, same
        # as every other rule.
        gated = self.check_confidence_gate(context, config)
        if gated is not None:
            gated.input_snapshot = self._snapshot(inputs)
            return gated

        # 2. Deterministic comparison via the shared threshold utility.
        comparison = compare_against_threshold(
            value=inputs.document_interest_rate,
            limit=config.max_interest_rate,
            direction=ComparisonDirection.MAX,
            value_label="Document interest rate",
            limit_label="interest rate",
        )

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            rule_version=self.rule_version,
            status=comparison.status,
            expected_value=config.max_interest_rate,
            actual_value=inputs.document_interest_rate,
            difference=comparison.difference,
            tolerance=Decimal(0),
            message=comparison.message,
            source="configured business rule (max_interest_rate)",
            confidence=context.confidence,
            input_snapshot=self._snapshot(inputs),
        )

    @staticmethod
    def _snapshot(inputs: InterestRateValidationInput) -> dict:
        return {"document_interest_rate": str(inputs.document_interest_rate)}
