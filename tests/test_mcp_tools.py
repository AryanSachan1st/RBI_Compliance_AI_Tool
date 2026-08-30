"""
tests/test_mcp_tools.py

Tests mcp_server/tools.py directly — the plain Python functions, not the
MCP protocol layer. This file deliberately does NOT import the `mcp`
package (server.py does), so it runs with the exact same
`pip install pydantic pytest` you already have, no extra dependency.

These tests mostly check that the wrapper correctly round-trips into
JSON-safe output (Decimals -> strings, enum -> string, etc.) — the actual
rule logic is already covered by test_emi.py / test_interest.py /
test_disclosure.py, so it isn't re-tested here.
"""

from mcp_server.tools import validate_disclosures, validate_emi, validate_interest_rate


class TestValidateEmiTool:
    def test_returns_json_safe_pass_result(self):
        result = validate_emi(
            principal="100000",
            annual_interest_rate="12",
            tenure_months="12",
            document_emi="8884.88",
            confidence=0.95,
        )

        assert result["status"] == "PASS"
        assert result["rule_id"] == "EMI-001"
        assert isinstance(result["expected_value"], str)  # Decimal -> str
        assert isinstance(result["timestamp"], str)  # datetime -> str

    def test_missing_confidence_is_uncertain_not_an_exception(self):
        result = validate_emi(
            principal="100000",
            annual_interest_rate="12",
            tenure_months="12",
            document_emi="8884.88",
        )

        assert result["status"] == "UNCERTAIN"

    def test_document_id_and_clause_id_pass_through(self):
        result = validate_emi(
            principal="100000",
            annual_interest_rate="12",
            tenure_months="12",
            document_emi="8884.88",
            confidence=0.9,
            document_id="DOC-42",
            clause_id="C7",
        )

        assert result["status"] == "PASS"  # confirms the call succeeded end-to-end


class TestValidateInterestRateTool:
    def test_returns_json_safe_result(self):
        result = validate_interest_rate(document_interest_rate="14", confidence=0.9)

        assert result["rule_id"] == "INTEREST-001"
        assert result["status"] in ("PASS", "FAIL")
        assert isinstance(result["actual_value"], str)

    def test_over_limit_fails(self):
        result = validate_interest_rate(document_interest_rate="99", confidence=0.9)
        assert result["status"] == "FAIL"


class TestValidateDisclosuresTool:
    def test_returns_json_safe_result(self):
        result = validate_disclosures(
            document_fields={
                "annual_percentage_rate": "14.5%",
                "processing_fee": "2500",
                "prepayment_penalty": "2%",
                "grievance_redressal_contact": "test@example.test",
            },
            confidence=0.9,
        )

        assert result["rule_id"] == "DISCLOSURE-001"
        assert result["status"] == "PASS"

    def test_missing_fields_fail_with_names_in_message(self):
        result = validate_disclosures(document_fields={}, confidence=0.9)

        assert result["status"] == "FAIL"
        assert "annual_percentage_rate" in result["message"]
