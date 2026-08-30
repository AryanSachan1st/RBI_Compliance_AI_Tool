"""
models/numeric_extraction_model.py

NEW FILE — added for Rule Engine <-> FastAPI integration.

Defines the structured output schema for the new numeric-field
extraction step (services/numeric_extraction_service.py). This is the
missing piece flagged in INTEGRATION_NOTES.md and RULE_ENGINE_README.md:
models/clause_model.py's ExtractedClause only carries free text
(clause_id, clause_type, clause_text) — nothing here replaces or edits
that model. This is a new, separate model for a new, separate
extraction task: pulling out the specific numbers rule_engine/ needs.

Every field is Optional[str] and defaults to None. The LLM is
instructed (see system_prompts/numeric_extraction_prompt.py) to leave a
field as None rather than guess or infer a value that is not explicitly
stated in the document — an absent field should mean "not found", not
"assumed to be zero" or "assumed to match some example". Fields stay as
str (not int/Decimal) here because that's exactly what
mcp_server/tools.py's validate_* functions already expect as input
(they parse the numeric types internally, same as EMICheckIn in
routes/compliance_routes.py passes str(payload.principal) rather than
a raw Decimal).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedLoanNumerics(BaseModel):
    """
    Structured numeric fields pulled from a loan document by the LLM,
    for handing directly to rule_engine/ (via mcp_server/tools.py).

    Maps to the three existing rules:
      - EMI-001 needs: principal, annual_interest_rate, tenure_months, document_emi
      - INTEREST-001 needs: annual_interest_rate (reused as the document's
        stated interest rate — same underlying figure)
      - DISCLOSURE-001 needs: annual_percentage_rate, processing_fee,
        prepayment_penalty, grievance_redressal_contact
    """

    principal: Optional[str] = Field(
        default=None,
        description="Loan principal amount as stated in the document, digits only, e.g. '100000'. None if not explicitly stated.",
    )
    annual_interest_rate: Optional[str] = Field(
        default=None,
        description="Annual interest rate as a percent, e.g. '12' for 12%. None if not explicitly stated.",
    )
    tenure_months: Optional[str] = Field(
        default=None,
        description="Loan tenure in months, e.g. '12'. Convert years to months if the document states years. None if not explicitly stated.",
    )
    document_emi: Optional[str] = Field(
        default=None,
        description="The EMI (equated monthly installment) amount as explicitly stated in the document. None if not explicitly stated.",
    )
    annual_percentage_rate: Optional[str] = Field(
        default=None,
        description="The disclosed annual percentage rate (APR) field, if the document has one separate from the plain interest rate. None if not found.",
    )
    processing_fee: Optional[str] = Field(
        default=None,
        description="Stated loan processing fee, as written in the document (keep any currency symbol/words as-is). None if not found.",
    )
    prepayment_penalty: Optional[str] = Field(
        default=None,
        description="Stated prepayment/foreclosure penalty terms, as written in the document. None if not found.",
    )
    grievance_redressal_contact: Optional[str] = Field(
        default=None,
        description="Stated grievance redressal contact (email, phone, or officer name), as written in the document. None if not found.",
    )
    extraction_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Overall confidence 0.0-1.0 that the fields extracted above are "
            "accurate and were explicitly present in the document (not "
            "inferred/guessed). This is NOT a fixed constant -- it must "
            "reflect genuine uncertainty, e.g. lower if the document is "
            "scanned/garbled, ambiguous, or several fields were left None."
        ),
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional short note on anything ambiguous, contradictory, or uncertain about the extracted fields. None if there is nothing to flag.",
    )
