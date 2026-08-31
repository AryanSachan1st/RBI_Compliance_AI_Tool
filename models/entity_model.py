"""Structured LLM extraction contract for deterministic compliance checks."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    entity_type: str = Field(description="date, monetary_amount, interest_rate, tenure, EMI, APR, or compliance_term")
    value: str = Field(description="Exact value as written in the document; do not normalize or calculate it.")
    source_text: str = Field(description="The smallest document excerpt supporting this value.")
    page_number: Optional[int] = Field(default=None, ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class LoanVerificationInputs(BaseModel):
    principal: Optional[str] = None
    annual_interest_rate: Optional[str] = None
    tenure_months: Optional[str] = None
    document_emi: Optional[str] = None
    annual_percentage_rate: Optional[str] = None


class StructuredDocumentEntities(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    loan_verification_inputs: LoanVerificationInputs = Field(default_factory=LoanVerificationInputs)
    disclosure_fields: dict[str, Optional[str]] = Field(default_factory=dict)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: list[str] = Field(default_factory=list)
