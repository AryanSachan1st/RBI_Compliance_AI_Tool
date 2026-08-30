"""
rule_engine/rules/emi.py

EMI-001: EMI Validation.

This is the canonical example from Section 5 of the master prompt: the LLM
might say "EMI appears compliant," but this rule independently recalculates
the expected EMI using the standard reducing-balance formula and compares
it against the EMI stated in the document. Deterministic result overrides
LLM output for this numerical check (Section 5, Section 23).

Formula (standard amortizing loan EMI):
    r = monthly_rate = annual_interest_rate / 12 / 100
    n = tenure_months
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)      if r > 0
    EMI = P / n                                     if r == 0 (interest-free)

Uses Decimal throughout (Section 27) — financial calculations must not use
naive binary float, since that introduces rounding error that could flip
a PASS/FAIL verdict near a tolerance boundary.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext

from pydantic import BaseModel, Field, field_validator

from rule_engine.base import Rule
from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.result import RuleResult

# Enough precision for intermediate (1+r)^n calculations before we round
# the final EMI to 2 decimal places (paise). 28 significant digits is
# Decimal's default and is more than sufficient here.
getcontext().prec = 28

TWO_PLACES = Decimal("0.01")


class EMIValidationInput(BaseModel):
    """Typed, validated inputs for EMI-001."""

    principal: Decimal = Field(..., description="Loan principal amount.")
    annual_interest_rate: Decimal = Field(
        ..., description="Annual interest rate as a percentage, e.g. 12 for 12%."
    )
    tenure_months: int = Field(..., description="Loan tenure in months.")
    document_emi: Decimal = Field(
        ..., description="EMI amount as stated in the document being checked."
    )

    @field_validator("principal", "document_emi")
    @classmethod
    def _must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be a positive amount")
        return v

    @field_validator("annual_interest_rate")
    @classmethod
    def _rate_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("interest rate cannot be negative")
        return v

    @field_validator("tenure_months")
    @classmethod
    def _tenure_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("tenure_months must be a positive integer")
        return v


class EMIValidationRule(Rule[EMIValidationInput]):
    rule_id = "EMI-001"
    rule_name = "EMI Validation"
    rule_version = "1.0.0"

    def evaluate(
        self,
        inputs: EMIValidationInput,
        context: RuleContext,
        config: RuleEngineConfig,
    ) -> RuleResult:
        # 1. Confidence gate (BR-01) — checked before anything else.
        gated = self.check_confidence_gate(context, config)
        if gated is not None:
            gated.input_snapshot = self._snapshot(inputs)
            return gated

        # 2. Calculate the expected EMI deterministically.
        try:
            expected_emi = self._calculate_emi(
                principal=inputs.principal,
                annual_interest_rate=inputs.annual_interest_rate,
                tenure_months=inputs.tenure_months,
            )
        except (InvalidOperation, ZeroDivisionError, ArithmeticError) as exc:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                rule_version=self.rule_version,
                status="UNCERTAIN",
                message="EMI could not be calculated from the given inputs.",
                source="deterministic calculation",
                confidence=context.confidence,
                input_snapshot=self._snapshot(inputs),
                error=str(exc),
            )

        # 3. Compare against the document's stated EMI, within tolerance.
        difference = abs(expected_emi - inputs.document_emi)
        tolerance = self._effective_tolerance(expected_emi, config)

        status = "PASS" if difference <= tolerance else "FAIL"
        message = (
            f"Document EMI {inputs.document_emi} is within the allowed "
            f"tolerance of the calculated EMI {expected_emi}."
            if status == "PASS"
            else f"Document EMI {inputs.document_emi} differs from the "
            f"calculated EMI {expected_emi} by {difference}, exceeding the "
            f"allowed tolerance of {tolerance}."
        )

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            rule_version=self.rule_version,
            status=status,
            expected_value=expected_emi,
            actual_value=inputs.document_emi,
            difference=difference,
            tolerance=tolerance,
            message=message,
            source="deterministic calculation (standard amortizing EMI formula)",
            confidence=context.confidence,
            input_snapshot=self._snapshot(inputs),
        )

    @staticmethod
    def _calculate_emi(
        principal: Decimal, annual_interest_rate: Decimal, tenure_months: int
    ) -> Decimal:
        n = tenure_months
        monthly_rate = annual_interest_rate / Decimal(12) / Decimal(100)

        if monthly_rate == 0:
            emi = principal / Decimal(n)
        else:
            one_plus_r_to_n = (Decimal(1) + monthly_rate) ** n
            emi = (
                principal
                * monthly_rate
                * one_plus_r_to_n
                / (one_plus_r_to_n - Decimal(1))
            )

        return emi.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _effective_tolerance(expected_emi: Decimal, config: RuleEngineConfig) -> Decimal:
        """Uses the larger of the absolute and percentage-based tolerance,
        if a percentage tolerance is configured."""
        absolute = config.emi_tolerance_absolute
        if config.emi_tolerance_percentage is None:
            return absolute

        percentage_based = (expected_emi * config.emi_tolerance_percentage / Decimal(100)).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        return max(absolute, percentage_based)

    @staticmethod
    def _snapshot(inputs: EMIValidationInput) -> dict:
        # Financial figures only, no customer-identifying text (Section 11/25).
        return {
            "principal": str(inputs.principal),
            "annual_interest_rate": str(inputs.annual_interest_rate),
            "tenure_months": inputs.tenure_months,
            "document_emi": str(inputs.document_emi),
        }
