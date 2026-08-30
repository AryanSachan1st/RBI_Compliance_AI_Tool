"""
rule_engine/result.py

Defines the structured output contract that EVERY deterministic rule must
return. This is Section 10 of the master prompt ("RULE RESULT CONTRACT").

Why this exists as its own module:
    The LLM/agent layer, the MCP tool layer, and any HTTP route all need to
    consume the SAME shape of result. If every rule returned a different
    ad-hoc dict, nothing downstream (audit logging, MCP tool responses,
    dashboards) could rely on a consistent structure. This is the one
    canonical schema for "what did a deterministic check decide".

No canonical compliance-result model exists elsewhere in the repo yet
(Aryan's ClauseAnalysis model is an LLM risk narrative, not a PASS/FAIL/
UNCERTAIN verdict) — so this is a new model, not a reuse of an existing one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer


class RuleStatus(str, Enum):
    """
    The three decision states required by Section 6 of the master prompt.

    PASS      - all required inputs present, rule succeeded.
    FAIL      - all required inputs present, rule failed.
    UNCERTAIN - required data missing/malformed/ambiguous, OR confidence
                below the configured threshold (BR-01). This is never
                silently converted to PASS.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class RuleResult(BaseModel):
    """
    The structured, auditable result of evaluating ONE deterministic rule
    against ONE set of inputs.

    Every field here maps directly to something Section 11 (Auditability)
    or Section 10 (Rule Result Contract) requires. Nothing here is
    speculative — if a field isn't populated, it's None, never guessed.
    """

    # --- Identity of the rule that produced this result ---
    rule_id: str = Field(..., description="Stable identifier, e.g. 'EMI-001'.")
    rule_name: str = Field(..., description="Human-readable name, e.g. 'EMI Validation'.")
    rule_version: str = Field(default="1.0.0", description="Version of the rule logic itself.")

    # --- The verdict ---
    status: RuleStatus

    # --- Numbers involved in the decision (rule-specific, so kept generic) ---
    expected_value: Optional[Decimal] = Field(
        default=None, description="Value the deterministic calculation produced."
    )
    actual_value: Optional[Decimal] = Field(
        default=None, description="Value found in the document/input."
    )
    difference: Optional[Decimal] = Field(
        default=None, description="abs(expected_value - actual_value), if both are numeric."
    )
    tolerance: Optional[Decimal] = Field(
        default=None, description="Allowed tolerance used for the PASS/FAIL comparison."
    )

    # --- Explanation ---
    message: str = Field(..., description="Human-readable explanation of the verdict.")
    source: str = Field(
        ..., description="Where the rule/threshold came from, e.g. 'configured business rule'."
    )

    # --- Confidence and auditability (Section 7 / Section 11) ---
    confidence: Optional[float] = Field(
        default=None, description="Extraction confidence that fed this rule, if applicable."
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        description="Normalized inputs used for this evaluation, for audit trail purposes. "
        "Do not put raw customer-identifying text here (Section 11 / 25).",
    )
    error: Optional[str] = Field(
        default=None, description="Populated only when evaluation could not complete cleanly."
    )

    @field_serializer(
        "expected_value", "actual_value", "difference", "tolerance", when_used="json"
    )
    def _serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        # Decimal doesn't JSON-serialize by default; make results easy to
        # dump for audit logs / MCP tool responses without extra glue code.
        return None if value is None else str(value)
