from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from modules.ml.space_optimizer import SpaceOptimizerDataPipeline, SpaceOptimizerModel


def test_pipeline_builds_examples() -> None:
    pipeline = SpaceOptimizerDataPipeline()
    training_set = pipeline.prepare_training_data()

    assert training_set.feature_names == (
        "idle_hours",
        "deliveries_count",
        "avg_delivery_duration_hours",
    )
    assert len(training_set.features) == 4
    assert len(training_set.labels) == 4
    # ensure ordering is stable for reproducible tests
    first_example = training_set.examples[0]
    assert first_example.previous_booking_id == "bk-1001"
    assert first_example.next_booking_id == "bk-1002"
    assert first_example.idle_hours == 3.0
    assert first_example.deliveries_count == 2
    assert round(first_example.avg_delivery_duration_hours, 4) == round((30 + 20) / 2 / 60, 4)
    assert first_example.label == 1


def test_pipeline_build_features_for_window() -> None:
    pipeline = SpaceOptimizerDataPipeline()
    window_start = datetime(2024, 1, 2, 15, tzinfo=timezone.utc)
    window_end = datetime(2024, 1, 2, 18, tzinfo=timezone.utc)

    features = pipeline.build_features_for_window("kitchen-1", window_start, window_end)
    idle_hours, deliveries_count, avg_delivery_duration = features
    # previous booking (bk-1003) ends at 11:00 -> 4 hours idle before window
    assert round(idle_hours, 4) == 4.0
    # deliveries between 11:00 and 15:00 include the early-morning restock
    assert deliveries_count == 1
    assert round(avg_delivery_duration, 4) == round(35 / 60, 4)


def test_model_training_and_persistence(tmp_path: Path) -> None:
    pipeline = SpaceOptimizerDataPipeline()
    training_set = pipeline.prepare_training_data()

    model = SpaceOptimizerModel(learning_rate=0.1, epochs=4000)
    model.fit(training_set.features, training_set.labels)
    accuracy = model.score(training_set.features, training_set.labels)
    assert accuracy >= 0.75

    artifact = tmp_path / "model.json"
    model.save(artifact)
    loaded = SpaceOptimizerModel.load(artifact)
    assert loaded.predict(training_set.features) == model.predict(training_set.features)
