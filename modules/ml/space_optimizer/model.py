"""Lightweight logistic regression used for idle window predictions."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass(slots=True)
class PredictionResult:
    """Encapsulates a single prediction produced by the model."""

    probability: float
    label: int


class SpaceOptimizerModel:
    """Minimal logistic regression with gradient descent optimisation."""

    def __init__(self, learning_rate: float = 0.05, epochs: int = 2000) -> None:
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        self.learning_rate = learning_rate
        self.epochs = epochs
        self._weights: List[float] | None = None  # bias + feature weights

    def fit(self, features: Sequence[Sequence[float]], labels: Sequence[int]) -> None:
        """Fit the logistic regression parameters using batch gradient descent."""

        if not features:
            raise ValueError("features cannot be empty")
        if len(features) != len(labels):
            raise ValueError("features and labels must have identical lengths")

        n_features = len(features[0])
        for row in features:
            if len(row) != n_features:
                raise ValueError("feature vectors must all have the same length")

        weights = [0.0] * (n_features + 1)  # bias term + per-feature weights

        for _ in range(self.epochs):
            gradients = [0.0] * (n_features + 1)
            for x_row, label in zip(features, labels):
                prediction = self._sigmoid(self._linear(weights, x_row))
                error = prediction - label
                gradients[0] += error  # bias gradient
                for index, value in enumerate(x_row, start=1):
                    gradients[index] += error * value

            step = self.learning_rate / len(features)
            for index in range(len(weights)):
                weights[index] -= step * gradients[index]

        self._weights = weights

    def predict_proba(self, features: Sequence[Sequence[float]]) -> List[float]:
        """Return probabilities for each feature vector."""

        weights = self._ensure_weights()
        probabilities: List[float] = []
        for x_row in features:
            probabilities.append(self._sigmoid(self._linear(weights, x_row)))
        return probabilities

    def predict(self, features: Sequence[Sequence[float]], threshold: float = 0.5) -> List[int]:
        """Return hard predictions using the provided probability threshold."""

        return [1 if probability >= threshold else 0 for probability in self.predict_proba(features)]

    def score(self, features: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
        """Compute simple accuracy for the provided dataset."""

        if len(features) != len(labels):
            raise ValueError("features and labels must have identical lengths")
        predictions = self.predict(features)
        correct = sum(1 for predicted, label in zip(predictions, labels) if predicted == label)
        return correct / len(labels)

    def save(self, path: Path | str) -> None:
        """Persist the trained model weights to disk."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "weights": self._ensure_weights(),
        }
        path.write_text(json.dumps(payload))

    @classmethod
    def load(cls, path: Path | str) -> "SpaceOptimizerModel":
        """Load a previously persisted model."""

        path = Path(path)
        payload = json.loads(path.read_text())
        model = cls(learning_rate=payload["learning_rate"], epochs=payload["epochs"])
        model._weights = [float(value) for value in payload["weights"]]
        return model

    @staticmethod
    def _linear(weights: Sequence[float], features: Sequence[float]) -> float:
        return weights[0] + sum(weight * value for weight, value in zip(weights[1:], features))

    @staticmethod
    def _sigmoid(value: float) -> float:
        # clamp to avoid math overflow in extreme cases
        value = max(min(value, 60.0), -60.0)
        return 1.0 / (1.0 + math.exp(-value))

    def _ensure_weights(self) -> List[float]:
        if self._weights is None:
            raise RuntimeError("Model has not been fitted yet")
        return self._weights


__all__ = ["PredictionResult", "SpaceOptimizerModel"]
