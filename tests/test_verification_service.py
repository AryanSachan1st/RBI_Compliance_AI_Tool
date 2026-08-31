from models.entity_model import StructuredDocumentEntities
from services.verification_service import _numeric_value, _tenure_months, run_deterministic_verifications


def test_normalizes_document_display_format_without_inference():
    assert _numeric_value("₹1,00,000.50") == "100000.50"
    assert _numeric_value("12.5%") == "12.5"
    assert _numeric_value(None) == ""
    assert _tenure_months("2 years") == "24"
    assert _tenure_months("18 months") == "18"


def test_structured_entities_feed_all_deterministic_rules():
    entities = StructuredDocumentEntities(
        loan_verification_inputs={
            "principal": "₹1,00,000",
            "annual_interest_rate": "12%",
            "tenure_months": "12 months",
            "document_emi": "₹8,884.88",
        },
        disclosure_fields={
            "annual_percentage_rate": "12%",
            "processing_fee": "₹2,500",
            "prepayment_penalty": "Nil",
            "grievance_redressal_contact": "help@example.test",
        },
        overall_confidence=0.95,
    )
    results = run_deterministic_verifications(entities, document_id="doc-1")
    assert [result["rule_id"] for result in results] == ["EMI-001", "INTEREST-001", "DISCLOSURE-001"]
    assert [result["status"] for result in results] == ["PASS", "PASS", "PASS"]
    assert all(result["confidence"] == 0.95 for result in results)


def test_low_extraction_confidence_forces_uncertain_results():
    entities = StructuredDocumentEntities(overall_confidence=0.2)
    results = run_deterministic_verifications(entities)
    assert all(result["status"] == "UNCERTAIN" for result in results)
