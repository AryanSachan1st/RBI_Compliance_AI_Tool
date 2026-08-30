"""
services/rule_validation_service.py

NEW FILE — added for Rule Engine <-> FastAPI integration.

This is the actual connective piece: takes the LLM-extracted numeric
fields (ExtractedLoanNumerics) and runs each rule_engine/ check that has
enough data to run, for a single document.

No rule logic is duplicated here. Every check below is a direct call to
mcp_server.tools -- the exact same functions already used by
mcp_server/server.py (the MCP tool layer) and already covered by
tests/test_mcp_tools.py. If a validation result looks wrong, the bug is
in rule_engine/ or mcp_server/tools.py, not here.

A field the extractor could not find (None) means the corresponding
check is SKIPPED, not run with a fabricated placeholder value. Silently
substituting "0" or "" for a missing number would produce a real-looking
FAIL/PASS that is actually meaningless -- worse than clearly saying "not
enough data was extracted to run this check."
"""

from __future__ import annotations

from typing import Any, Optional

from models.numeric_extraction_model import ExtractedLoanNumerics
from mcp_server.tools import validate_disclosures, validate_emi, validate_interest_rate


def run_rule_validations(
    numerics: ExtractedLoanNumerics,
    document_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Runs EMI-001, INTEREST-001, and DISCLOSURE-001 against whichever
    extracted fields are available, and returns a list of result dicts.

    Each entry is EITHER:
      - a real RuleResult dict (same shape returned by
        mcp_server.tools.validate_*, i.e. rule_id, status, message,
        expected_value, etc.), or
      - a distinctly-shaped "skipped" marker (rule_id, skipped: true,
        reason) when the extraction did not provide enough data to run
        that check at all.

    These two shapes are deliberately different (a skipped entry has NO
    `status` field) so a caller can never mistake "we didn't run this"
    for an actual PASS/FAIL/UNCERTAIN verdict from rule_engine/.
    """
    results: list[dict[str, Any]] = []
    confidence = numerics.extraction_confidence
    source = "llm_extraction"

    # --- EMI-001 ---
    if all([
        numerics.principal,
        numerics.annual_interest_rate,
        numerics.tenure_months,
        numerics.document_emi,
    ]):
        results.append(
            validate_emi(
                principal=numerics.principal,
                annual_interest_rate=numerics.annual_interest_rate,
                tenure_months=numerics.tenure_months,
                document_emi=numerics.document_emi,
                confidence=confidence,
                document_id=document_id,
                source=source,
            )
        )
    else:
        results.append(
            _skipped(
                "EMI-001",
                "principal, annual_interest_rate, tenure_months, and document_emi were not all extracted",
            )
        )

    # --- INTEREST-001 ---
    if numerics.annual_interest_rate:
        results.append(
            validate_interest_rate(
                document_interest_rate=numerics.annual_interest_rate,
                confidence=confidence,
                document_id=document_id,
                source=source,
            )
        )
    else:
        results.append(_skipped("INTEREST-001", "annual_interest_rate was not extracted"))

    # --- DISCLOSURE-001 ---
    # This one always runs, even with every field missing -- detecting
    # missing disclosures IS the point of this rule, so "nothing was
    # extracted" is a legitimate (and informative) FAIL input, not a
    # reason to skip.
    disclosure_fields = {
        "annual_percentage_rate": numerics.annual_percentage_rate,
        "processing_fee": numerics.processing_fee,
        "prepayment_penalty": numerics.prepayment_penalty,
        "grievance_redressal_contact": numerics.grievance_redressal_contact,
    }
    results.append(
        validate_disclosures(
            document_fields=disclosure_fields,
            confidence=confidence,
            document_id=document_id,
            source=source,
        )
    )

    return results


def _skipped(rule_id: str, reason: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "skipped": True,
        "reason": reason,
    }
