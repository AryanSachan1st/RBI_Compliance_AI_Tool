"""Bridge structured LLM entities to authoritative deterministic rule checks."""
from __future__ import annotations

import re
from typing import Any

from mcp_server.tools import validate_disclosures, validate_emi, validate_interest_rate
from models.entity_model import StructuredDocumentEntities


def _numeric_value(value: str | None) -> str:
    """Normalize display formatting only; never infer a missing value."""
    if value is None:
        return ""
    cleaned = value.replace(",", "").replace("₹", "").replace("%", "").strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    return match.group(0) if match else ""


def _tenure_months(value: str | None) -> str:
    if value is None:
        return ""
    numeric = _numeric_value(value)
    if not numeric:
        return ""
    if "year" in value.lower():
        return str(int(float(numeric) * 12))
    return numeric


def run_deterministic_verifications(
    entities: StructuredDocumentEntities,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run authoritative checks using only explicitly extracted entity values.

    Every check is retained, including UNCERTAIN outcomes, so missing or low
    confidence extractions remain visible to the human reviewer (BR-01).
    """
    inputs = entities.loan_verification_inputs
    confidence = entities.overall_confidence
    common = {
        "confidence": confidence,
        "document_id": document_id,
        "source": "llm_structured_extraction",
    }
    return [
        validate_emi(
            principal=_numeric_value(inputs.principal),
            annual_interest_rate=_numeric_value(inputs.annual_interest_rate),
            tenure_months=_tenure_months(inputs.tenure_months),
            document_emi=_numeric_value(inputs.document_emi),
            **common,
        ),
        validate_interest_rate(
            document_interest_rate=_numeric_value(inputs.annual_interest_rate),
            **common,
        ),
        validate_disclosures(document_fields=entities.disclosure_fields, **common),
    ]
