"""
rule_engine/rules/disclosure.py

DISCLOSURE-001: Mandatory Disclosure Validation.

Checks that a configured set of required disclosure fields are present
(and non-empty) in the document's extracted fields (Section 8). This is a
presence/completeness check, not a numeric comparison, so it doesn't go
through the `threshold` module — but it shares the same confidence gate
as every other rule (Section 7 / BR-01), and returns the same RuleResult
contract.

IMPORTANT — placeholder field list: `required_disclosure_fields` in
config.py is an illustrative placeholder list, not a sourced-from-
regulation enumeration of every disclosure RBI/IRDAI actually requires.
Replace it once the team has an authoritative list.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from rule_engine.base import Rule
from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.result import RuleResult


class DisclosureValidationInput(BaseModel):
    """
    Typed, validated inputs for DISCLOSURE-001.

    `document_fields` maps disclosure field name -> extracted value.
    A field that is absent from the dict, or present with an empty/
    whitespace-only value, counts as missing.
    """

    document_fields: dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Extracted disclosure field name -> value (None/empty if absent).",
    )


class DisclosureValidationRule(Rule[DisclosureValidationInput]):
    rule_id = "DISCLOSURE-001"
    rule_name = "Mandatory Disclosure Validation"
    rule_version = "1.0.0"

    def evaluate(
        self,
        inputs: DisclosureValidationInput,
        context: RuleContext,
        config: RuleEngineConfig,
    ) -> RuleResult:
        # 1. Confidence gate (BR-01) — checked before anything else.
        gated = self.check_confidence_gate(context, config)
        if gated is not None:
            gated.input_snapshot = self._snapshot(inputs)
            return gated

        # 2. Deterministic presence check against the configured field list.
        required = config.required_disclosure_fields
        missing = [
            field
            for field in required
            if not (inputs.document_fields.get(field) or "").strip()
        ]

        if missing:
            status = "FAIL"
            message = (
                "The following mandatory disclosure fields are missing or "
                f"empty: {', '.join(missing)}."
            )
        else:
            status = "PASS"
            message = (
                f"All {len(required)} mandatory disclosure fields are "
                f"present: {', '.join(required)}."
            )

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            rule_version=self.rule_version,
            status=status,
            message=message,
            source="configured business rule (required_disclosure_fields)",
            confidence=context.confidence,
            input_snapshot=self._snapshot(inputs),
        )

    @staticmethod
    def _snapshot(inputs: DisclosureValidationInput) -> dict:
        # Field names + presence only; avoid dumping full disclosure text
        # verbatim into the audit trail (Section 11/25 caution about not
        # storing raw customer-identifying text).
        return {
            "fields_provided": sorted(inputs.document_fields.keys()),
        }
