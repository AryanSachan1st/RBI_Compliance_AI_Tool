"""
rule_engine/context.py

RuleContext carries everything about WHERE a set of inputs came from,
as opposed to the inputs themselves. This separation matters because the
confidence-gating requirement (BR-01, Section 7) applies uniformly across
every rule, regardless of what the rule actually calculates.

IMPORTANT — integration gap, stated explicitly (not glossed over):
    Aryan's current pipeline (services/core_langchain_service.py) does not
    extract structured numeric entities (principal, interest_rate, tenure,
    emi) — only free-text clauses. So today, `confidence` and the document/
    clause identifiers below will typically be supplied manually or by a
    caller other than Aryan's module, until entity extraction exists.
    RuleContext is deliberately generic so it works either way.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RuleContext(BaseModel):
    """
    Metadata about the provenance of the inputs being validated.

    confidence:
        Extraction confidence, 0.0-1.0. This is what BR-01 checks against
        the configured threshold. If the caller has no confidence signal
        (e.g. a compliance officer typed the numbers in by hand), pass 1.0
        to indicate "not extracted, treated as ground truth" — do NOT pass
        None to mean "trust it fully"; None instead triggers UNCERTAIN,
        since a missing confidence signal is itself something to flag for
        review rather than silently assume is fine.
    """

    document_id: Optional[str] = None
    clause_id: Optional[str] = None
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="0.0-1.0 extraction confidence."
    )
    source: str = Field(
        default="manual_input",
        description="Where these values came from, e.g. 'manual_input', "
        "'llm_extraction', 'ocr_extraction'.",
    )
    extra: dict[str, Any] = Field(default_factory=dict)
