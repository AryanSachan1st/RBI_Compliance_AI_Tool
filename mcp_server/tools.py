"""
mcp_server/tools.py

Plain, framework-independent Python functions wrapping RuleExecutor. This
module deliberately imports NOTHING MCP-specific — it's the integration
point for anyone who wants to call the rule engine directly, without
speaking the MCP protocol at all.

This is the file to import if Aryan's pipeline (or a FastAPI route, or a
notebook, or anything else) just wants to call a rule and get a JSON-safe
dict back:

    from mcp_server.tools import validate_emi
    result = validate_emi(
        principal="100000",
        annual_interest_rate="12",
        tenure_months="12",
        document_emi="8900",
        confidence=0.95,
    )

Every function here:
  - takes plain JSON-representable types (str/float/dict), matching what
    an LLM tool-call or an HTTP request body would actually send
  - builds a RuleContext and calls RuleExecutor.execute() — never touches
    rule_engine internals or reimplements any comparison logic (Section 15)
  - returns result.model_dump(mode="json"): a plain dict, Decimals and
    the status enum already converted to JSON-safe strings, so callers
    never need to know this was built with pydantic

A single shared RuleExecutor is built at import time from the default
registry and config (env-overridable — see rule_engine/config.py). If
Aryan's project needs a different config (e.g. different thresholds per
environment), construct a fresh RuleExecutor there and don't rely on the
module-level singleton below.
"""

from __future__ import annotations

from typing import Any, Optional

from rule_engine.context import RuleContext
from rule_engine.executor import RuleExecutor
from rule_engine.registry import build_default_registry

# Shared executor instance. Cheap to build (no I/O), safe to share across
# calls since Rule subclasses are stateless (see rule_engine/base.py).
_executor = RuleExecutor(build_default_registry())


def _context(
    confidence: Optional[float],
    document_id: Optional[str],
    clause_id: Optional[str],
    source: str,
) -> RuleContext:
    return RuleContext(
        confidence=confidence,
        document_id=document_id,
        clause_id=clause_id,
        source=source,
    )


def validate_emi(
    principal: str,
    annual_interest_rate: str,
    tenure_months: str,
    document_emi: str,
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict[str, Any]:
    """
    Validate a stated EMI (equated monthly installment) against the
    amortization formula, within the configured tolerance (EMI-001).

    Args:
        principal: Loan principal amount, e.g. "100000".
        annual_interest_rate: Annual interest rate as a percent, e.g. "12" for 12%.
        tenure_months: Loan tenure in months, e.g. "12".
        document_emi: The EMI as stated in the document, e.g. "8900".
        confidence: Extraction confidence 0.0-1.0. Pass 1.0 for manually
            entered/verified data. Omitting this (None) forces an
            UNCERTAIN result per BR-01 — it is not treated as "trusted".
        document_id: Optional source document identifier, for audit trail.
        clause_id: Optional source clause identifier, for audit trail.
        source: Where these values came from, e.g. "manual_input",
            "llm_extraction", "ocr_extraction".

    Returns:
        A JSON-safe dict matching the RuleResult contract: rule_id,
        status ("PASS"/"FAIL"/"UNCERTAIN"), message, expected_value,
        actual_value, difference, tolerance, confidence, timestamp, etc.
    """
    result = _executor.execute(
        "EMI-001",
        raw_inputs={
            "principal": principal,
            "annual_interest_rate": annual_interest_rate,
            "tenure_months": tenure_months,
            "document_emi": document_emi,
        },
        context=_context(confidence, document_id, clause_id, source),
    )
    return result.model_dump(mode="json")


def validate_interest_rate(
    document_interest_rate: str,
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict[str, Any]:
    """
    Validate a document's stated annual interest rate against the
    configured maximum permissible rate (INTEREST-001).

    NOTE: the configured maximum (rule_engine/config.py: max_interest_rate)
    is a PLACEHOLDER, not a sourced regulatory ceiling. Replace it via the
    RULE_ENGINE_MAX_INTEREST_RATE env var (or a custom RuleEngineConfig)
    before relying on FAIL results for anything real.

    Args:
        document_interest_rate: Annual interest rate as stated in the
            document, e.g. "14" for 14%.
        confidence: Extraction confidence 0.0-1.0. See validate_emi for
            the None-means-UNCERTAIN behavior.
        document_id: Optional source document identifier, for audit trail.
        clause_id: Optional source clause identifier, for audit trail.
        source: Where this value came from, e.g. "manual_input",
            "llm_extraction", "ocr_extraction".

    Returns:
        A JSON-safe dict matching the RuleResult contract.
    """
    result = _executor.execute(
        "INTEREST-001",
        raw_inputs={"document_interest_rate": document_interest_rate},
        context=_context(confidence, document_id, clause_id, source),
    )
    return result.model_dump(mode="json")


def validate_disclosures(
    document_fields: dict[str, Optional[str]],
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict[str, Any]:
    """
    Validate that all mandatory disclosure fields are present and
    non-empty in a document's extracted fields (DISCLOSURE-001).

    NOTE: the configured required field list
    (rule_engine/config.py: required_disclosure_fields) is a PLACEHOLDER
    illustrative list, not a sourced-from-regulation enumeration. Replace
    it via RULE_ENGINE_REQUIRED_DISCLOSURE_FIELDS (comma-separated) or a
    custom RuleEngineConfig before relying on FAIL results for anything
    real.

    Args:
        document_fields: Mapping of disclosure field name -> extracted
            value. A field that is absent, None, or empty/whitespace-only
            counts as missing.
        confidence: Extraction confidence 0.0-1.0. See validate_emi for
            the None-means-UNCERTAIN behavior.
        document_id: Optional source document identifier, for audit trail.
        clause_id: Optional source clause identifier, for audit trail.
        source: Where these values came from, e.g. "manual_input",
            "llm_extraction", "ocr_extraction".

    Returns:
        A JSON-safe dict matching the RuleResult contract.
    """
    result = _executor.execute(
        "DISCLOSURE-001",
        raw_inputs={"document_fields": document_fields},
        context=_context(confidence, document_id, clause_id, source),
    )
    return result.model_dump(mode="json")
