"""Batch job that retrains the space optimizer model."""

from __future__ import annotations

from pathlib import Path

from apps.bookings import BookingHistoryRepository
from apps.logistics import DeliveryLogRepository
from modules.ml.space_optimizer import SpaceOptimizerDataPipeline, SpaceOptimizerModel

MODEL_PATH = Path("modules/ml/space_optimizer/model_state.json")


def train_and_store_model(model_path: Path = MODEL_PATH) -> SpaceOptimizerModel:
    """Train the space optimizer model and persist it to ``model_path``."""

    pipeline = SpaceOptimizerDataPipeline(
        booking_repo=BookingHistoryRepository(),
        logistics_repo=DeliveryLogRepository(),
    )
    training_set = pipeline.prepare_training_data()
    model = SpaceOptimizerModel()
    model.fit(training_set.features, training_set.labels)
    model.save(model_path)
    return model


if __name__ == "__main__":
    train_and_store_model()
