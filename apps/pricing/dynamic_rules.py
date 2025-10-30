"""Dynamic pricing rules based on utilization metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, Sequence


@dataclass(slots=True)
class UtilizationMetrics:
    """Container for utilization signals used by the pricing engine."""

    utilization_rate: float
    active_bookings: int = 0
    cancellation_rate: float = 0.0

    def clamp(self) -> "UtilizationMetrics":
        """Return a metrics instance with values normalized to sane ranges."""

        rate = min(max(self.utilization_rate, 0.0), 1.0)
        cancellations = max(self.cancellation_rate, 0.0)
        return UtilizationMetrics(
            utilization_rate=rate,
            active_bookings=max(self.active_bookings, 0),
            cancellation_rate=cancellations,
        )


@dataclass(slots=True)
class RuleEvaluation:
    """Outcome of an individual pricing rule evaluation."""

    discount: float = 0.0
    reason: str | None = None


class PricingRule(Protocol):
    """Protocol implemented by pricing rules."""

    def evaluate(self, metrics: UtilizationMetrics) -> RuleEvaluation:
        """Return the discount (0.0-1.0) recommended by this rule."""


@dataclass(slots=True)
class PricingDecision:
    """Aggregate pricing decision returned by the rule engine."""

    discount: float
    applied_rules: list[str]


@dataclass(slots=True)
class UnderUtilizationRule:
    """Apply a discount when utilization drops below a threshold."""

    threshold: float
    discount: float
    reason: str = "low_utilization"

    def evaluate(self, metrics: UtilizationMetrics) -> RuleEvaluation:
        normalized = metrics.clamp()
        if normalized.utilization_rate < self.threshold:
            return RuleEvaluation(discount=self.discount, reason=self.reason)
        return RuleEvaluation()


class DynamicPricingRuleEngine:
    """Evaluate pricing rules against utilization metrics."""

    def __init__(self, rules: Sequence[PricingRule] | None = None) -> None:
        self._rules: list[PricingRule] = list(rules or [])

    def with_rule(self, rule: PricingRule) -> "DynamicPricingRuleEngine":
        """Return a new engine with ``rule`` appended to the rule list."""

        return DynamicPricingRuleEngine([*self._rules, rule])

    def evaluate(self, metrics: UtilizationMetrics) -> PricingDecision:
        applied: list[str] = []
        discounts: list[float] = []
        for rule in self._rules:
            result = rule.evaluate(metrics)
            discount = max(0.0, result.discount)
            if discount > 0.0:
                applied.append(result.reason or rule.__class__.__name__)
                discounts.append(discount)
        discount = max(discounts, default=0.0)
        discount = min(discount, 1.0)
        return PricingDecision(discount=discount, applied_rules=applied)

    def extend(self, rules: Iterable[PricingRule]) -> "DynamicPricingRuleEngine":
        """Return a new engine with rules from ``rules`` appended."""

        return DynamicPricingRuleEngine([*self._rules, *rules])


_DEFAULT_ENGINE = DynamicPricingRuleEngine(
    [UnderUtilizationRule(threshold=0.5, discount=0.15)]
)


def build_default_engine() -> DynamicPricingRuleEngine:
    """Return a copy of the default pricing engine."""

    return DynamicPricingRuleEngine(_DEFAULT_ENGINE._rules)


__all__ = [
    "UtilizationMetrics",
    "RuleEvaluation",
    "PricingRule",
    "PricingDecision",
    "UnderUtilizationRule",
    "DynamicPricingRuleEngine",
    "build_default_engine",
]
