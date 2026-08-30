"""
tests/test_emi.py

Covers the Section 26 minimum test matrix for EMI-001:
  - valid case -> PASS
  - invalid case -> FAIL
  - missing/invalid data -> UNCERTAIN
  - boundary case (exactly at tolerance) -> PASS
  - floating-point / rounding case -> tolerance handled correctly
  - low confidence -> UNCERTAIN regardless of the numbers (BR-01)
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.registry import build_default_registry
from rule_engine.executor import RuleExecutor
from rule_engine.rules.emi import EMIValidationInput, EMIValidationRule


@pytest.fixture
def rule() -> EMIValidationRule:
    return EMIValidationRule()


@pytest.fixture
def config() -> RuleEngineConfig:
    return RuleEngineConfig()  # placeholder defaults: confidence 0.80, tolerance ₹1.00


@pytest.fixture
def confident_context() -> RuleContext:
    return RuleContext(confidence=0.95, source="manual_input")


class TestEMICalculation:
    def test_valid_emi_passes(self, rule, config, confident_context):
        # principal=100000, rate=12%, tenure=12 months -> known correct EMI ≈ 8884.88
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8884.88"),
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert result.expected_value == Decimal("8884.88")
        assert result.difference == Decimal("0.00")

    def test_incorrect_emi_fails(self, rule, config, confident_context):
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8900.00"),  # document overstates EMI
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        assert result.difference > result.tolerance

    def test_zero_interest_rate_uses_simple_division(self, rule, config, confident_context):
        inputs = EMIValidationInput(
            principal=Decimal("120000"),
            annual_interest_rate=Decimal("0"),
            tenure_months=12,
            document_emi=Decimal("10000.00"),
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert result.expected_value == Decimal("10000.00")


class TestBoundaryAndTolerance:
    def test_difference_exactly_at_tolerance_passes(self, rule, confident_context):
        # tolerance = ₹1.00 exactly; difference of exactly ₹1.00 must PASS
        # (per Section 26: "exactly at threshold -> expected per configured operator";
        # we treat <= tolerance as PASS, so equal-to-tolerance passes).
        config = RuleEngineConfig(emi_tolerance_absolute=Decimal("1.00"))
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8885.88"),  # exactly 1.00 above 8884.88
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert result.difference == Decimal("1.00")

    def test_difference_just_over_tolerance_fails(self, rule, confident_context):
        config = RuleEngineConfig(emi_tolerance_absolute=Decimal("1.00"))
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8885.89"),  # 1.01 above -> just over tolerance
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"

    def test_percentage_tolerance_used_when_larger(self, rule, confident_context):
        # 1% of ~8884.88 ≈ 88.85, much larger than the ₹1.00 absolute default
        config = RuleEngineConfig(
            emi_tolerance_absolute=Decimal("1.00"),
            emi_tolerance_percentage=Decimal("1"),
        )
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8950.00"),  # within 1% but outside ₹1.00
        )
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"


class TestMissingOrInvalidData:
    def test_negative_principal_rejected_at_input_validation(self):
        with pytest.raises(ValidationError):
            EMIValidationInput(
                principal=Decimal("-100000"),
                annual_interest_rate=Decimal("12"),
                tenure_months=12,
                document_emi=Decimal("8900"),
            )

    def test_zero_tenure_rejected_at_input_validation(self):
        with pytest.raises(ValidationError):
            EMIValidationInput(
                principal=Decimal("100000"),
                annual_interest_rate=Decimal("12"),
                tenure_months=0,
                document_emi=Decimal("8900"),
            )

    def test_missing_field_via_executor_returns_uncertain_not_exception(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.95)

        result = executor.execute(
            "EMI-001",
            raw_inputs={
                "principal": "100000",
                # annual_interest_rate missing entirely
                "tenure_months": 12,
                "document_emi": "8900",
            },
            context=context,
        )

        assert result.status == "UNCERTAIN"
        assert result.error is not None


class TestConfidenceGate:
    def test_low_confidence_forces_uncertain_even_with_correct_numbers(self, rule, config):
        low_confidence_context = RuleContext(confidence=0.42, source="ocr_extraction")
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8884.88"),  # numerically correct
        )
        result = rule.evaluate(inputs, low_confidence_context, config)

        assert result.status == "UNCERTAIN"
        assert "BR-01" in result.message or "confidence" in result.message.lower()

    def test_missing_confidence_forces_uncertain(self, rule, config):
        no_confidence_context = RuleContext(confidence=None)
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8884.88"),
        )
        result = rule.evaluate(inputs, no_confidence_context, config)

        assert result.status == "UNCERTAIN"

    def test_confidence_exactly_at_threshold_proceeds(self, rule, config):
        exact_context = RuleContext(confidence=0.80)  # == default threshold
        inputs = EMIValidationInput(
            principal=Decimal("100000"),
            annual_interest_rate=Decimal("12"),
            tenure_months=12,
            document_emi=Decimal("8884.88"),
        )
        result = rule.evaluate(inputs, exact_context, config)

        assert result.status == "PASS"  # gate is "< threshold", so == threshold passes through


class TestExecutorIntegration:
    def test_unknown_rule_id_returns_uncertain(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.95)

        result = executor.execute("NON-EXISTENT-999", raw_inputs={}, context=context)

        assert result.status == "UNCERTAIN"
        assert result.error is not None

    def test_full_pass_through_executor(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.95, document_id="doc-1", clause_id="C1")

        result = executor.execute(
            "EMI-001",
            raw_inputs={
                "principal": "100000",
                "annual_interest_rate": "12",
                "tenure_months": 12,
                "document_emi": "8884.88",
            },
            context=context,
        )

        assert result.status == "PASS"
        assert result.rule_id == "EMI-001"
