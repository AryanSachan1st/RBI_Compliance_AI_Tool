"""
demo.py

Standalone demonstration of the rule engine. Deliberately has ZERO
dependency on FastAPI, LangChain, or an OpenAI key — this module is
runnable/testable in complete isolation from Aryan's pipeline.

Covers all rules built so far:
    EMI-001         (Phase 1)
    INTEREST-001    (Phase 2)
    DISCLOSURE-001  (Phase 2)

Run with:
    python demo.py
"""

from __future__ import annotations

from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.executor import RuleExecutor
from rule_engine.registry import build_default_registry


def run_case(
    executor: RuleExecutor,
    title: str,
    rule_id: str,
    raw_inputs: dict,
    context: RuleContext,
) -> None:
    print(f"\n--- {title} ---")
    result = executor.execute(rule_id, raw_inputs, context)
    print(f"rule:            {result.rule_id}")
    print(f"status:          {result.status}")
    print(f"message:         {result.message}")
    if result.expected_value is not None:
        print(f"expected_value:  {result.expected_value}")
        print(f"actual_value:    {result.actual_value}")
        print(f"difference:      {result.difference}")
        print(f"tolerance:       {result.tolerance}")
    if result.error:
        print(f"error:           {result.error}")


def main() -> None:
    registry = build_default_registry()
    config = RuleEngineConfig()  # placeholder thresholds — see config.py
    executor = RuleExecutor(registry, config)

    print(f"Registered rules: {registry.list_rule_ids()}")
    print(f"Confidence threshold (BR-01): {config.confidence_threshold}")
    print(f"EMI tolerance: \u20b9{config.emi_tolerance_absolute}")
    print(f"Max interest rate: {config.max_interest_rate}%")
    print(f"Required disclosure fields: {config.required_disclosure_fields}")

    # ============================ EMI-001 (Phase 1) ============================

    run_case(
        executor,
        "EMI-001 — Section 5 example: document EMI overstated",
        "EMI-001",
        raw_inputs={
            "principal": "100000",
            "annual_interest_rate": "12",
            "tenure_months": "12",
            "document_emi": "8900",
        },
        context=RuleContext(
            document_id="DOC-001", clause_id="C1", confidence=0.95, source="manual_input"
        ),
    )

    run_case(
        executor,
        "EMI-001 — correctly stated EMI",
        "EMI-001",
        raw_inputs={
            "principal": "100000",
            "annual_interest_rate": "12",
            "tenure_months": "12",
            "document_emi": "8884.88",
        },
        context=RuleContext(confidence=0.98, source="manual_input"),
    )

    run_case(
        executor,
        "EMI-001 — Section 7 example: low-confidence extraction",
        "EMI-001",
        raw_inputs={
            "principal": "100000",
            "annual_interest_rate": "12",
            "tenure_months": "12",
            "document_emi": "8884.88",
        },
        context=RuleContext(confidence=0.42, source="ocr_extraction"),
    )

    run_case(
        executor,
        "EMI-001 — missing required field",
        "EMI-001",
        raw_inputs={
            "principal": "100000",
            "tenure_months": "12",
            "document_emi": "8900",
        },
        context=RuleContext(confidence=0.9),
    )

    # ========================= INTEREST-001 (Phase 2) ==========================

    run_case(
        executor,
        "INTEREST-001 — Section 8 example: rate within configured maximum",
        "INTEREST-001",
        raw_inputs={"document_interest_rate": "14"},
        context=RuleContext(
            document_id="DOC-002", clause_id="C1", confidence=0.92, source="manual_input"
        ),
    )

    run_case(
        executor,
        "INTEREST-001 — rate exceeds configured maximum",
        "INTEREST-001",
        raw_inputs={"document_interest_rate": "24"},
        context=RuleContext(confidence=0.9, source="llm_extraction"),
    )

    run_case(
        executor,
        "INTEREST-001 — low-confidence extraction forces UNCERTAIN",
        "INTEREST-001",
        raw_inputs={"document_interest_rate": "14"},
        context=RuleContext(confidence=0.35, source="ocr_extraction"),
    )

    # ======================== DISCLOSURE-001 (Phase 2) =========================

    run_case(
        executor,
        "DISCLOSURE-001 — all mandatory fields present",
        "DISCLOSURE-001",
        raw_inputs={
            "document_fields": {
                "annual_percentage_rate": "14.5%",
                "processing_fee": "\u20b92,500",
                "prepayment_penalty": "2% of outstanding principal",
                "grievance_redressal_contact": "grievance@example-bank.test",
            }
        },
        context=RuleContext(
            document_id="DOC-003", clause_id="C5", confidence=0.9, source="manual_input"
        ),
    )

    run_case(
        executor,
        "DISCLOSURE-001 — required fields missing",
        "DISCLOSURE-001",
        raw_inputs={
            "document_fields": {
                "annual_percentage_rate": "14.5%",
                # processing_fee, prepayment_penalty, grievance_redressal_contact absent
            }
        },
        context=RuleContext(confidence=0.9, source="llm_extraction"),
    )

    run_case(
        executor,
        "DISCLOSURE-001 — low-confidence extraction forces UNCERTAIN",
        "DISCLOSURE-001",
        raw_inputs={
            "document_fields": {
                "annual_percentage_rate": "14.5%",
                "processing_fee": "\u20b92,500",
                "prepayment_penalty": "2% of outstanding principal",
                "grievance_redressal_contact": "grievance@example-bank.test",
            }
        },
        context=RuleContext(confidence=0.4, source="ocr_extraction"),
    )


if __name__ == "__main__":
    main()
