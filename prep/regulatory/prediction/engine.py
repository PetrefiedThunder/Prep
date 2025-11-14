"""Predictive analytics for regulatory compliance risk."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PredictionResult:
    """Normalized prediction output for compliance risk."""

    compliance_probability: float
    risk_factors: list[str]
    recommended_actions: list[str]


class CompliancePredictor:
    """Predict future compliance risk using historical and real-time features."""

    def __init__(self, model: Any | None = None) -> None:
        self.features = [
            "risk_score",
            "days_since_inspection",
            "insurance_coverage",
            "zoning_compliance",
        ]
        self._sklearn_available = self._check_sklearn()
        self.model = model or self._create_default_model()
        self._trained = False

    async def predict_compliance_risk(self, kitchen_data: dict[str, Any]) -> PredictionResult:
        """Predict the probability of a kitchen remaining compliant."""

        feature_vector = self.extract_features(kitchen_data)
        probability = self._predict_probability(feature_vector)
        risk_factors = self.identify_risk_factors(feature_vector)
        actions = self.generate_actions(probability)
        return PredictionResult(
            compliance_probability=probability,
            risk_factors=risk_factors,
            recommended_actions=actions,
        )

    def train(self, dataset: Iterable[dict[str, Any]], labels: Iterable[int]) -> None:
        """Train the underlying model using a labeled dataset."""

        if not self.model:
            logger.warning("No ML model available; skipping training.")
            return

        feature_matrix = [self.extract_features(item) for item in dataset]
        try:
            self.model.fit(feature_matrix, list(labels))
        except Exception as exc:  # pragma: no cover - depends on sklearn availability
            logger.error("Training failed: %s", exc)
            return
        self._trained = True

    def extract_features(self, kitchen_data: dict[str, Any]) -> list[float]:
        """Extract numeric feature vector from kitchen metadata."""

        return [
            float(kitchen_data.get("risk_score", 0.0)),
            float(kitchen_data.get("days_since_inspection", 0.0)),
            float(kitchen_data.get("insurance_coverage", 0.0)),
            float(kitchen_data.get("zoning_compliance", 1.0)),
        ]

    def identify_risk_factors(self, features: list[float]) -> list[str]:
        """Identify potential risk contributors from the feature vector."""

        risk_factors: list[str] = []
        if features[0] > 70:
            risk_factors.append("High historical risk score")
        if features[1] > 365:
            risk_factors.append("Overdue for health inspection")
        if features[2] < 1_000_000:
            risk_factors.append("Inadequate insurance coverage")
        if features[3] < 1.0:
            risk_factors.append("Unresolved zoning compliance issues")
        return risk_factors

    def generate_actions(self, probability: float) -> list[str]:
        """Generate recommended mitigation actions based on predicted probability."""

        if probability >= 0.8:
            return ["Maintain current compliance routines", "Schedule next inspection proactively"]
        if probability >= 0.5:
            return [
                "Conduct internal compliance audit",
                "Verify insurance coverage meets jurisdictional minimums",
            ]
        return [
            "Engage compliance consultant",
            "Increase inspection cadence",
            "Update training for food safety staff",
        ]

    def _predict_probability(self, feature_vector: list[float]) -> float:
        if self.model and self._trained:
            try:
                proba = self.model.predict_proba([feature_vector])[0]
                return float(proba[1])
            except Exception as exc:  # pragma: no cover - depends on sklearn API
                logger.error("Model prediction failed: %s", exc)
        # heuristic fallback
        baseline = 1.0 - min(feature_vector[0] / 100.0, 1.0)
        inspection_factor = 0.5 if feature_vector[1] > 180 else 1.0
        insurance_factor = min(feature_vector[2] / 1_000_000, 1.0)
        zoning_factor = max(feature_vector[3], 0.0)
        probability = baseline * inspection_factor * 0.5 + 0.5 * insurance_factor * zoning_factor
        return max(0.0, min(probability, 1.0))

    def _check_sklearn(self) -> bool:
        try:
            importlib.import_module("sklearn")
        except ModuleNotFoundError:
            logger.warning(
                "scikit-learn not installed; falling back to heuristic compliance prediction."
            )
            return False
        return True

    def _create_default_model(self) -> Any | None:
        if not self._sklearn_available:
            return None
        try:
            ensemble = importlib.import_module("sklearn.ensemble")
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            logger.warning("sklearn.ensemble unavailable; predictions will use heuristic fallback.")
            return None
        RandomForestClassifier = ensemble.RandomForestClassifier
        return RandomForestClassifier(n_estimators=100, random_state=42)


__all__ = ["CompliancePredictor", "PredictionResult"]
