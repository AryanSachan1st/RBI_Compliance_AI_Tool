"""
rule_engine/threshold.py

Shared comparison logic for "document value vs a configured limit" rules.

Section 9 of the master prompt calls for reusable validation logic instead
of duplicating the same comparison + message-formatting code inside every
rule that reduces to "is X over/under a configured threshold". EMI-001
already has its own tolerance logic (it's a two-sided closeness check, not
a one-sided limit, so it doesn't fit this shape). INTEREST-001 is the first
rule that DOES fit this shape, and this module is what it uses instead of
hand-rolling its own comparison.

Any future one-sided threshold rule (e.g. a maximum processing fee, a
minimum notice period) should use this too, rather than re-implementing it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ComparisonDirection(str, Enum):
    """Which side of the limit is compliant."""

    MAX = "max"  # value must be <= limit to comply
    MIN = "min"  # value must be >= limit to comply


@dataclass(frozen=True)
class ThresholdComparison:
    """Result of comparing a single value against a single configured limit."""

    status: str  # "PASS" or "FAIL"
    difference: Decimal  # how far past the limit, 0 if compliant
    message: str


def compare_against_threshold(
    *,
    value: Decimal,
    limit: Decimal,
    direction: ComparisonDirection,
    value_label: str,
    limit_label: str,
) -> ThresholdComparison:
    """
    Compares `value` against `limit` in the given `direction` and returns a
    PASS/FAIL verdict with a human-readable message and the magnitude of
    the violation (0 if compliant).

    This function does NOT touch confidence gating (BR-01) — that stays in
    Rule.check_confidence_gate, since it's cross-cutting and unrelated to
    the shape of the comparison itself. Callers run the confidence gate
    first and only reach this function once the gate has cleared.
    """
    if direction is ComparisonDirection.MAX:
        compliant = value <= limit
        difference = max(value - limit, Decimal(0))
        bound_word = "maximum"
    else:
        compliant = value >= limit
        difference = max(limit - value, Decimal(0))
        bound_word = "minimum"

    if compliant:
        status = "PASS"
        message = (
            f"{value_label} {value} complies with the configured "
            f"{bound_word} {limit_label} of {limit}."
        )
    else:
        status = "FAIL"
        message = (
            f"{value_label} {value} violates the configured {bound_word} "
            f"{limit_label} of {limit} by {difference}."
        )

    return ThresholdComparison(status=status, difference=difference, message=message)
