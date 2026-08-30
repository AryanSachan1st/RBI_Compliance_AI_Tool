"""
rule_engine/config.py

Section 28 requirement: regulatory/business thresholds must be configurable,
not scattered as magic numbers in the rule code. This module is the single
place those numbers live.

Follows the existing project's config pattern (config/settings.py uses
python-dotenv + os.getenv), rather than inventing a different config system.

IMPORTANT — these are NOT real RBI/IRDAI thresholds. Per Section 8/36 of
the master prompt, I am explicitly NOT fabricating regulatory values (e.g.
an actual maximum interest rate). The defaults below are placeholders
clearly marked as such; replace them with values sourced from the team's
actual regulatory repository/config once it exists.
"""

from __future__ import annotations

import os
from decimal import Decimal

from pydantic import BaseModel, Field


class RuleEngineConfig(BaseModel):
    """
    Central, versioned configuration for the deterministic rule engine.

    Every numeric default here is a PLACEHOLDER pending real regulatory
    data. Nothing in this file should be read as "the actual RBI rule."
    """

    # --- BR-01: confidence gating (Section 7) ---
    confidence_threshold: float = Field(
        default=0.80,
        description="Below this, verdict is forced to UNCERTAIN regardless "
        "of the calculation result. Business rule BR-01.",
    )

    # --- EMI validation tolerance (Section 8, EMI validation) ---
    emi_tolerance_absolute: Decimal = Field(
        default=Decimal("1.00"),
        description="Absolute rupee tolerance for EMI comparison. PLACEHOLDER "
        "— not sourced from an actual regulatory/business document.",
    )
    emi_tolerance_percentage: Decimal | None = Field(
        default=None,
        description="Optional percentage-of-expected-EMI tolerance, used "
        "instead of (whichever is larger vs.) the absolute tolerance if set.",
    )

    # --- Interest rate validation (Section 8, INTEREST-001) ---
    max_interest_rate: Decimal = Field(
        default=Decimal("18.00"),
        description="Maximum permissible annual interest rate (percent). "
        "PLACEHOLDER — not sourced from an actual regulatory ceiling. "
        "Replace once the team has a real, sourced maximum.",
    )

    # --- Mandatory disclosure validation (Section 8, DISCLOSURE-001) ---
    required_disclosure_fields: list[str] = Field(
        default_factory=lambda: [
            "annual_percentage_rate",
            "processing_fee",
            "prepayment_penalty",
            "grievance_redressal_contact",
        ],
        description="Disclosure field names that must be present (and "
        "non-empty) in an extracted document. PLACEHOLDER — this is an "
        "illustrative list, not a sourced-from-regulation enumeration of "
        "every disclosure actually required. Replace once the team has an "
        "authoritative list.",
    )

    # --- Rule metadata / versioning (Section 28) ---
    config_version: str = Field(default="0.1.0-placeholder")
    config_source: str = Field(
        default="local_defaults_pending_regulatory_data",
        description="Where these thresholds came from. Must be updated once "
        "a real regulatory data source is wired in.",
    )


def load_config() -> RuleEngineConfig:
    """
    Loads config with environment-variable overrides, mirroring the
    load_dotenv-based pattern already used in config/settings.py.

    Env vars (all optional, fall back to placeholder defaults above):
        RULE_ENGINE_CONFIDENCE_THRESHOLD
        RULE_ENGINE_EMI_TOLERANCE_ABSOLUTE
        RULE_ENGINE_EMI_TOLERANCE_PERCENTAGE
        RULE_ENGINE_MAX_INTEREST_RATE
        RULE_ENGINE_REQUIRED_DISCLOSURE_FIELDS  (comma-separated)
    """
    overrides: dict[str, object] = {}

    if val := os.getenv("RULE_ENGINE_CONFIDENCE_THRESHOLD"):
        overrides["confidence_threshold"] = float(val)
    if val := os.getenv("RULE_ENGINE_EMI_TOLERANCE_ABSOLUTE"):
        overrides["emi_tolerance_absolute"] = Decimal(val)
    if val := os.getenv("RULE_ENGINE_EMI_TOLERANCE_PERCENTAGE"):
        overrides["emi_tolerance_percentage"] = Decimal(val)
    if val := os.getenv("RULE_ENGINE_MAX_INTEREST_RATE"):
        overrides["max_interest_rate"] = Decimal(val)
    if val := os.getenv("RULE_ENGINE_REQUIRED_DISCLOSURE_FIELDS"):
        overrides["required_disclosure_fields"] = [
            field.strip() for field in val.split(",") if field.strip()
        ]

    return RuleEngineConfig(**overrides)
