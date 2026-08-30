"""
tests/test_disclosure.py

Covers the Section 26 minimum test matrix for DISCLOSURE-001:
  - all required fields present -> PASS
  - one or more required fields missing -> FAIL
  - a field present but empty/whitespace-only -> counts as missing -> FAIL
  - no fields provided at all -> FAIL, all required fields listed as missing
  - low confidence -> UNCERTAIN regardless of what fields are present (BR-01)
"""

import pytest

from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.registry import build_default_registry
from rule_engine.executor import RuleExecutor
from rule_engine.rules.disclosure import (
    DisclosureValidationInput,
    DisclosureValidationRule,
)


@pytest.fixture
def rule() -> DisclosureValidationRule:
    return DisclosureValidationRule()


@pytest.fixture
def config() -> RuleEngineConfig:
    # placeholder defaults: annual_percentage_rate, processing_fee,
    # prepayment_penalty, grievance_redressal_contact
    return RuleEngineConfig()


@pytest.fixture
def confident_context() -> RuleContext:
    return RuleContext(confidence=0.95, source="manual_input")


ALL_PRESENT = {
    "annual_percentage_rate": "14.5%",
    "processing_fee": "₹2,500",
    "prepayment_penalty": "2% of outstanding principal",
    "grievance_redressal_contact": "grievance@example-bank.test",
}


class TestDisclosurePresence:
    def test_all_fields_present_passes(self, rule, config, confident_context):
        inputs = DisclosureValidationInput(document_fields=ALL_PRESENT)
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "PASS"
        assert "annual_percentage_rate" in result.message

    def test_one_missing_field_fails(self, rule, config, confident_context):
        fields = dict(ALL_PRESENT)
        del fields["prepayment_penalty"]
        inputs = DisclosureValidationInput(document_fields=fields)
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        assert "prepayment_penalty" in result.message

    def test_empty_string_field_counts_as_missing(self, rule, config, confident_context):
        fields = dict(ALL_PRESENT)
        fields["processing_fee"] = "   "  # whitespace-only
        inputs = DisclosureValidationInput(document_fields=fields)
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        assert "processing_fee" in result.message

    def test_no_fields_provided_lists_all_as_missing(self, rule, config, confident_context):
        inputs = DisclosureValidationInput(document_fields={})
        result = rule.evaluate(inputs, confident_context, config)

        assert result.status == "FAIL"
        for field in config.required_disclosure_fields:
            assert field in result.message


class TestConfidenceGate:
    def test_low_confidence_forces_uncertain_even_when_all_present(self, rule, config):
        low_confidence_context = RuleContext(confidence=0.5, source="ocr_extraction")
        inputs = DisclosureValidationInput(document_fields=ALL_PRESENT)
        result = rule.evaluate(inputs, low_confidence_context, config)

        assert result.status == "UNCERTAIN"
        assert "BR-01" in result.message or "confidence" in result.message.lower()

    def test_missing_confidence_forces_uncertain(self, rule, config):
        no_confidence_context = RuleContext(confidence=None)
        inputs = DisclosureValidationInput(document_fields=ALL_PRESENT)
        result = rule.evaluate(inputs, no_confidence_context, config)

        assert result.status == "UNCERTAIN"


class TestExecutorIntegration:
    def test_full_pass_through_executor(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.9, document_id="doc-1", clause_id="C3")

        result = executor.execute(
            "DISCLOSURE-001",
            raw_inputs={"document_fields": ALL_PRESENT},
            context=context,
        )

        assert result.status == "PASS"
        assert result.rule_id == "DISCLOSURE-001"

    def test_full_fail_through_executor(self, config):
        registry = build_default_registry()
        executor = RuleExecutor(registry, config)
        context = RuleContext(confidence=0.9)

        result = executor.execute(
            "DISCLOSURE-001",
            raw_inputs={"document_fields": {"annual_percentage_rate": "14.5%"}},
            context=context,
        )

        assert result.status == "FAIL"
