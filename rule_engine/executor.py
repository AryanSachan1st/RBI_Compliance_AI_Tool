"""
rule_engine/executor.py

RuleExecutor is the single entry point for "run rule X against inputs Y".
Both the (future) HTTP routes and the (future) MCP tools should call
through this, not import individual rule classes directly — this is what
guarantees uncaught exceptions never leak a raw traceback (Section 24)
and always come back as a structured RuleResult instead.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from rule_engine.context import RuleContext
from rule_engine.config import RuleEngineConfig, load_config
from rule_engine.registry import RuleRegistry
from rule_engine.result import RuleResult


class RuleExecutor:
    def __init__(
        self,
        registry: RuleRegistry,
        config: RuleEngineConfig | None = None,
    ) -> None:
        self.registry = registry
        self.config = config or load_config()

    def execute(
        self,
        rule_id: str,
        raw_inputs: dict,
        context: RuleContext,
    ) -> RuleResult:
        """
        Looks up the rule, validates raw_inputs against its typed input
        model, and evaluates it. Never raises for expected failure modes
        (missing rule, invalid inputs) — those become UNCERTAIN results
        with `error` populated, per Section 24 (structured, useful errors,
        no stack traces exposed to callers).
        """
        try:
            rule = self.registry.get(rule_id)
        except KeyError as exc:
            return RuleResult(
                rule_id=rule_id,
                rule_name="unknown",
                status="UNCERTAIN",
                message=f"Rule '{rule_id}' is not registered.",
                source="rule_executor",
                error=str(exc),
            )

        input_model_cls = self._input_model_for(rule)
        try:
            typed_inputs = input_model_cls(**raw_inputs)
        except ValidationError as exc:
            return RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_version=rule.rule_version,
                status="UNCERTAIN",
                message="One or more inputs failed validation; manual review required.",
                source="input_validation",
                confidence=context.confidence,
                input_snapshot=raw_inputs,
                error=str(exc),
            )

        try:
            return rule.evaluate(typed_inputs, context, self.config)
        except Exception as exc:  # noqa: BLE001 - deliberate: never leak a bare traceback
            return RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_version=rule.rule_version,
                status="UNCERTAIN",
                message="An unexpected error occurred while evaluating this rule.",
                source="rule_executor",
                confidence=context.confidence,
                input_snapshot=raw_inputs,
                error=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _input_model_for(rule) -> type[BaseModel]:
        """
        Recovers the concrete Pydantic input model a Rule subclass declares
        via its Generic[InputT] parameterization, so the executor can
        validate raw dict input generically without a hardcoded rule_id
        -> model mapping that would need updating for every new rule.
        """
        for base in getattr(type(rule), "__orig_bases__", ()):
            args = getattr(base, "__args__", ())
            if args and issubclass(args[0], BaseModel):
                return args[0]
        raise TypeError(
            f"Could not determine input model for rule '{rule.rule_id}'. "
            "Ensure it subclasses Rule[YourInputModel]."
        )
