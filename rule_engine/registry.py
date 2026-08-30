"""
rule_engine/registry.py

A simple lookup table from rule_id -> Rule instance. Kept intentionally
minimal — this is NOT a rules-as-data system (no dynamic rule authoring),
just a registration point so the executor (and eventually MCP tools) can
find rules by ID without importing every rule module directly everywhere.
"""

from __future__ import annotations

from rule_engine.base import Rule


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"Rule '{rule.rule_id}' is already registered.")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Rule:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise KeyError(f"No rule registered with id '{rule_id}'.") from exc

    def list_rule_ids(self) -> list[str]:
        return sorted(self._rules.keys())


def build_default_registry() -> RuleRegistry:
    """Registers all rules built so far (Phase 1 + Phase 2). Extend this
    as new rules are added."""
    from rule_engine.rules.emi import EMIValidationRule
    from rule_engine.rules.interest import InterestRateValidationRule
    from rule_engine.rules.disclosure import DisclosureValidationRule

    registry = RuleRegistry()
    registry.register(EMIValidationRule())
    registry.register(InterestRateValidationRule())
    registry.register(DisclosureValidationRule())
    return registry
