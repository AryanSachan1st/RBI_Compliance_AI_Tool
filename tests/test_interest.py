"""
tests/test_interest.py

Covers the Section 26 minimum test matrix for INTEREST-001:
  - valid case (rate within limit) -> PASS
  - invalid case (rate exceeds limit) -> FAIL
  - boundary case (exactly at the configured maximum) -> PASS
  - missing/invalid data -> UNCERTAIN
  - low confidence -> UNCERTAIN regardless of the numbers (BR-01)
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.registry import build_default_registry
from rule_engine.executor import RuleExecutor
from rule_engine.rules.interest import (
    InterestRateValidationInput,
    InterestRateValidationRule,
)


@pytest.fixture
def rule() -> InterestRateValidationRule:
    return InterestRateValidationRule()


@pytest.fixture
def config() -> RuleEngineConfig:
    return RuleEngineConfig()  # placeholder default: max_interest_rate = 18.00


@pytest.fixture
def confident_context() -> RuleContext:
    return RuleContext(confidence=0.95, source="manual_input")


class TestInterestRateComparison:
    def test_rate_within_limit_passes(self, rule, config, confident_context):
        # Section 8 example: document states 14%, configured max is 18%.
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("14"))
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert result.actual_value == Decimal("14")
        assert result.expected_value == Decimal("18.00")
        assert result.difference == Decimal("0")

    def test_rate_over_limit_fails(self, rule, config, confident_context):
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("21"))
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        assert result.difference == Decimal("3.00")


class TestBoundary:
    def test_rate_exactly_at_maximum_passes(self, rule, confident_context):
        config = RuleEngineConfig(max_interest_rate=Decimal("18.00"))
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("18.00"))
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert result.difference == Decimal("0")

    def test_rate_just_over_maximum_fails(self, rule, confident_context):
        config = RuleEngineConfig(max_interest_rate=Decimal("18.00"))
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("18.01"))
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        assert result.difference == Decimal("0.01")


class TestMissingOrInvalidData:
    def test_negative_rate_rejected_at_input_validation(self):
        with pytest.raises(ValidationError):
            InterestRateValidationInput(document_interest_rate=Decimal("-5"))

    def test_missing_field_via_executor_returns_uncertain_not_exception(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.95)

        result = executor.execute(
            "INTEREST-001",
            raw_inputs={},  # document_interest_rate missing entirely
            context=context,
        )

        assert result.status == "UNCERTAIN"
        assert result.error is not None


class TestConfidenceGate:
    def test_low_confidence_forces_uncertain_even_with_compliant_rate(self, rule, config):
        low_confidence_context = RuleContext(confidence=0.3, source="ocr_extraction")
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("10"))
        result = rule.evaluate(inputs, low_confidence_context, config)

        assert result.status == "UNCERTAIN"
        assert "BR-01" in result.message or "confidence" in result.message.lower()

    def test_missing_confidence_forces_uncertain(self, rule, config):
        no_confidence_context = RuleContext(confidence=None)
        inputs = InterestRateValidationInput(document_interest_rate=Decimal("10"))
        result = rule.evaluate(inputs, no_confidence_context, config)

        assert result.status == "UNCERTAIN"


class TestExecutorIntegration:
    def test_full_pass_through_executor(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.9, document_id="doc-1", clause_id="C2")

        result = executor.execute(
            "INTEREST-001",
            raw_inputs={"document_interest_rate": "14"},
            context=context,
        )

        assert result.status == "PASS"
        assert result.rule_id == "INTEREST-001"

    def test_full_fail_through_executor(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.9)

        result = executor.execute(
            "INTEREST-001",
            raw_inputs={"document_interest_rate": "25"},
            context=context,
        )

        assert result.status == "FAIL"
