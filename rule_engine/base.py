"""
rule_engine/base.py

The abstract base every deterministic rule implements. Section 9 explicitly
forbids one giant validate_everything() function — this is the mechanism
that keeps rules modular and independently testable instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from rule_engine.config import RuleEngineConfig
from rule_engine.context import RuleContext
from rule_engine.result import RuleResult

# Each concrete rule defines its own typed input model (e.g. EMIValidationInput).
# The generic keeps evaluate() fully typed per-rule instead of taking `dict`.
InputT = TypeVar("InputT", bound=BaseModel)


class Rule(ABC, Generic[InputT]):
    """
    Base class for a single deterministic compliance rule.

    Subclasses must set `rule_id`, `rule_name`, and `rule_version` as class
    attributes, and implement `evaluate()`.

    Design intent: a Rule is stateless and side-effect free. It takes
    typed inputs + context + config, and returns a RuleResult. It never
    raises for "business" failure conditions (bad data, low confidence) —
    those become UNCERTAIN/FAIL results. It's fine for it to raise for
    genuine programming errors (e.g. a bug), which RuleExecutor catches
    and converts into a structured error result (Section 24).
    """

    rule_id: str
    rule_name: str
    rule_version: str = "1.0.0"

    @abstractmethod
    def evaluate(
        self,
        inputs: InputT,
        context: RuleContext,
        config: RuleEngineConfig,
    ) -> RuleResult:
        """Evaluate this rule against the given inputs. Must not raise for
        expected data-quality problems — return UNCERTAIN/FAIL instead."""
        raise NotImplementedError

    def check_confidence_gate(
        self, context: RuleContext, config: RuleEngineConfig
    ) -> RuleResult | None:
        """
        Shared BR-01 confidence check (Section 7), reusable by every rule
        so the logic isn't duplicated per-rule.

        Returns a RuleResult with status=UNCERTAIN if the gate is triggered,
        or None if the rule should proceed with normal evaluation.
        """
        if context.confidence is None:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                rule_version=self.rule_version,
                status="UNCERTAIN",
                message=(
                    "No extraction confidence was provided for these inputs. "
                    "Per BR-01, results without a confidence signal require "
                    "manual review rather than being treated as reliable."
                ),
                source="BR-01 confidence gate",
                confidence=None,
            )

        if context.confidence < config.confidence_threshold:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                rule_version=self.rule_version,
                status="UNCERTAIN",
                message=(
                    f"Extraction confidence {context.confidence:.2f} is below "
                    f"the configured threshold {config.confidence_threshold:.2f}. "
                    "Manual review required (BR-01)."
                ),
                source="BR-01 confidence gate",
                confidence=context.confidence,
            )

        return None
