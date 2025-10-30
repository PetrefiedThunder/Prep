"""Feature extraction pipeline for the space optimizer model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

from apps.bookings import Booking, BookingHistoryRepository
from apps.logistics import DeliveryLog, DeliveryLogRepository


@dataclass(slots=True)
class TrainingExample:
    """Structured representation of an idle window observation."""

    kitchen_id: str
    previous_booking_id: str
    next_booking_id: str
    window_start: datetime
    window_end: datetime
    idle_hours: float
    deliveries_count: int
    avg_delivery_duration_hours: float
    label: int

    def feature_vector(self) -> List[float]:
        return [
            float(self.idle_hours),
            float(self.deliveries_count),
            float(self.avg_delivery_duration_hours),
        ]


@dataclass(slots=True)
class TrainingSet:
    """Bundle containing features, labels and their metadata."""

    features: List[List[float]]
    labels: List[int]
    feature_names: Sequence[str]
    examples: List[TrainingExample]


class SpaceOptimizerDataPipeline:
    """Builds training data from historical bookings and delivery logs."""

    FEATURE_NAMES: Sequence[str] = ("idle_hours", "deliveries_count", "avg_delivery_duration_hours")

    def __init__(
        self,
        booking_repo: BookingHistoryRepository | None = None,
        logistics_repo: DeliveryLogRepository | None = None,
        idle_threshold_minutes: int = 120,
    ) -> None:
        self._booking_repo = booking_repo or BookingHistoryRepository()
        self._logistics_repo = logistics_repo or DeliveryLogRepository()
        self._idle_threshold_minutes = idle_threshold_minutes
        self._bookings_by_kitchen: Dict[str, List[Booking]] | None = None
        self._deliveries_by_kitchen: Dict[str, List[DeliveryLog]] | None = None

    @property
    def feature_names(self) -> Sequence[str]:
        return self.FEATURE_NAMES

    def prepare_training_data(self) -> TrainingSet:
        """Extract feature vectors and labels for supervised learning."""

        bookings_by_kitchen = self._load_bookings()
        deliveries_by_kitchen = self._load_deliveries()
        examples: List[TrainingExample] = []

        for kitchen_id, bookings in bookings_by_kitchen.items():
            if len(bookings) < 2:
                continue

            for previous, upcoming in zip(bookings, bookings[1:]):
                window_start = previous.end
                window_end = upcoming.start
                idle_minutes = max((window_end - window_start).total_seconds() / 60.0, 0.0)
                idle_hours = idle_minutes / 60.0

                deliveries = _deliveries_between(
                    deliveries_by_kitchen.get(kitchen_id, ()), window_start, window_end
                )
                deliveries_count = len(deliveries)
                avg_delivery_duration_hours = (
                    sum(delivery.duration_minutes for delivery in deliveries) / deliveries_count / 60.0
                    if deliveries_count
                    else 0.0
                )

                label = 1 if idle_minutes >= self._idle_threshold_minutes else 0

                example = TrainingExample(
                    kitchen_id=kitchen_id,
                    previous_booking_id=previous.booking_id,
                    next_booking_id=upcoming.booking_id,
                    window_start=window_start,
                    window_end=window_end,
                    idle_hours=idle_hours,
                    deliveries_count=deliveries_count,
                    avg_delivery_duration_hours=avg_delivery_duration_hours,
                    label=label,
                )
                examples.append(example)

        features = [example.feature_vector() for example in examples]
        labels = [example.label for example in examples]
        return TrainingSet(features=features, labels=labels, feature_names=self.FEATURE_NAMES, examples=examples)

    def build_features_for_window(
        self, kitchen_id: str, window_start: datetime, window_end: datetime
    ) -> List[float]:
        """Create a feature vector for an arbitrary candidate idle window."""

        bookings_by_kitchen = self._load_bookings()
        deliveries_by_kitchen = self._load_deliveries()
        bookings = bookings_by_kitchen.get(kitchen_id, [])

        previous = _latest_booking_before(bookings, window_start)
        idle_start = previous.end if previous else window_start
        idle_minutes = max((window_start - idle_start).total_seconds() / 60.0, 0.0)
        idle_hours = idle_minutes / 60.0

        deliveries = _deliveries_between(deliveries_by_kitchen.get(kitchen_id, ()), idle_start, window_start)
        deliveries_count = len(deliveries)
        avg_delivery_duration_hours = (
            sum(delivery.duration_minutes for delivery in deliveries) / deliveries_count / 60.0
            if deliveries_count
            else 0.0
        )

        return [float(idle_hours), float(deliveries_count), float(avg_delivery_duration_hours)]

    def _load_bookings(self) -> Dict[str, List[Booking]]:
        if self._bookings_by_kitchen is None:
            grouped: Dict[str, List[Booking]] = {}
            for booking in self._booking_repo.list_completed_bookings():
                grouped.setdefault(booking.kitchen_id, []).append(booking)
            for booking_list in grouped.values():
                booking_list.sort(key=lambda record: record.start)
            self._bookings_by_kitchen = grouped
        return self._bookings_by_kitchen

    def _load_deliveries(self) -> Dict[str, List[DeliveryLog]]:
        if self._deliveries_by_kitchen is None:
            grouped: Dict[str, List[DeliveryLog]] = {}
            for delivery in self._logistics_repo.list_completed_deliveries():
                grouped.setdefault(delivery.kitchen_id, []).append(delivery)
            for delivery_list in grouped.values():
                delivery_list.sort(key=lambda record: record.completed_at)
            self._deliveries_by_kitchen = grouped
        return self._deliveries_by_kitchen


def _deliveries_between(
    deliveries: Iterable[DeliveryLog], window_start: datetime, window_end: datetime
) -> List[DeliveryLog]:
    return [
        delivery
        for delivery in deliveries
        if window_start <= delivery.completed_at <= window_end
    ]


def _latest_booking_before(bookings: Iterable[Booking], reference: datetime) -> Booking | None:
    return max(
        (booking for booking in bookings if booking.end <= reference),
        default=None,
        key=lambda booking: booking.end,
    )
