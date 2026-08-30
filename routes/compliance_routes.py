"""
routes/compliance_routes.py

NEW FILE — added for Rule Engine <-> FastAPI integration.

This does NOT modify or replace anything in routes/document_routes.py,
services/core_langchain_service.py, services/document_controller.py, or
any other existing file in this project. It exposes the already-built,
already-tested rule_engine/ (Phase 1-3, by Venu) as its own set of HTTP
endpoints, callable independently of Aryan's LLM/RAG pipeline.

WHY A SEPARATE ROUTER INSTEAD OF WIRING INTO /upload-doc/:
    Aryan's pipeline (services/core_langchain_service.py) currently
    extracts only free-text clauses -- {clause_id, clause_type,
    clause_text} -- via the LLM. There is no step anywhere in that
    pipeline that produces the structured numeric entities (principal,
    interest rate, tenure, EMI, disclosure field values) that
    rule_engine/ requires as typed input.

    Wiring the rule engine directly into /upload-doc/'s output right now
    would require either:
      (a) fabricating a numeric-entity-extraction step here, or
      (b) guessing numbers out of free clause text with regex,
    and both of those would mean inventing behavior that was never built
    or verified -- which this project's rules explicitly avoid.

    Instead, this router lets any caller who ALREADY HAS the structured
    numbers -- a human compliance officer typing them in (see static/
    for a basic testing UI), or a future numeric-entity-extraction step
    once Aryan's team builds one -- call the deterministic rule engine
    directly over HTTP. This is the "direct Python import" integration
    shape documented in RULE_ENGINE_README.md, just exposed as routes.

    Once real numeric-entity-extraction exists on Aryan's side, that
    step can call these same rule_engine/executor.py functions directly
    (in-process) or hit these endpoints -- the contract does not change.

Every response is the same structured RuleResult (PASS/FAIL/UNCERTAIN)
the standalone rule engine already returns via demo.py / pytest -- no
new response shape invented for HTTP.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from rule_engine.context import RuleContext
from rule_engine.executor import RuleExecutor
from rule_engine.registry import build_default_registry

router = APIRouter(prefix="/compliance", tags=["deterministic rule engine"])

# Built once at import time, same pattern as demo.py / test files.
_registry = build_default_registry()
_executor = RuleExecutor(_registry)


class ContextIn(BaseModel):
    """
    Mirrors rule_engine.context.RuleContext, exposed as a request body
    field so callers can (optionally) supply provenance/confidence.

    confidence defaults to 1.0 here (not None) because the primary
    caller today is a human typing numbers into the testing UI --
    "not extracted, treated as ground truth" per RuleContext's own
    docstring. A future automated caller (e.g. real entity extraction)
    should explicitly pass its own real confidence value instead of
    relying on this default.
    """

    document_id: Optional[str] = None
    clause_id: Optional[str] = None
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "manual_input"


class EMICheckIn(BaseModel):
    principal: Decimal
    annual_interest_rate: Decimal
    tenure_months: int
    document_emi: Decimal
    context: ContextIn = Field(default_factory=ContextIn)


class InterestRateCheckIn(BaseModel):
    document_interest_rate: Decimal
    context: ContextIn = Field(default_factory=ContextIn)


class DisclosureCheckIn(BaseModel):
    document_fields: dict[str, Optional[str]] = Field(default_factory=dict)
    context: ContextIn = Field(default_factory=ContextIn)


def _execute(rule_id: str, raw_inputs: dict, context_in: ContextIn):
    context = RuleContext(**context_in.model_dump())
    return _executor.execute(rule_id=rule_id, raw_inputs=raw_inputs, context=context)


@router.get("/rules")
def list_rules() -> dict:
    """Lists the rule IDs currently registered in the deterministic engine."""
    return {"rules": _registry.list_rule_ids()}


@router.post("/validate/emi")
def validate_emi(payload: EMICheckIn):
    return _execute(
        "EMI-001",
        {
            "principal": str(payload.principal),
            "annual_interest_rate": str(payload.annual_interest_rate),
            "tenure_months": payload.tenure_months,
            "document_emi": str(payload.document_emi),
        },
        payload.context,
    )


@router.post("/validate/interest-rate")
def validate_interest_rate(payload: InterestRateCheckIn):
    return _execute(
        "INTEREST-001",
        {"document_interest_rate": str(payload.document_interest_rate)},
        payload.context,
    )


@router.post("/validate/disclosures")
def validate_disclosures(payload: DisclosureCheckIn):
    return _execute(
        "DISCLOSURE-001",
        {"document_fields": payload.document_fields},
        payload.context,
    )
