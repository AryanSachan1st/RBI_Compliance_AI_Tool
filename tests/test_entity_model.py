import pytest
from pydantic import ValidationError

from models.entity_model import ExtractedEntity, StructuredDocumentEntities


def test_structured_entities_preserve_source_values_for_rule_inputs():
    payload = StructuredDocumentEntities(
        entities=[ExtractedEntity(entity_type="EMI", value="₹8,884.88", source_text="EMI: ₹8,884.88", confidence=0.94)],
        loan_verification_inputs={"principal": "₹1,00,000", "annual_interest_rate": "12%", "tenure_months": "12", "document_emi": "₹8,884.88"},
        disclosure_fields={"processing_fee": "₹2,500"},
        overall_confidence=0.91,
    )
    assert payload.loan_verification_inputs.document_emi == "₹8,884.88"
    assert payload.entities[0].source_text == "EMI: ₹8,884.88"


def test_entity_confidence_must_be_a_probability():
    with pytest.raises(ValidationError):
        ExtractedEntity(entity_type="date", value="01/01/2026", source_text="Date: 01/01/2026", confidence=1.2)
