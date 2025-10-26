"""Utilities for validating certificate of insurance (COI) documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import List


@dataclass(slots=True)
class COIValidationResult:
    """Result of a COI validation attempt."""

    valid: bool
    expiry_date: datetime
    errors: List[str]


def validate_coi(payload: bytes) -> COIValidationResult:
    """Validate the uploaded COI PDF payload.

    The current implementation performs lightweight sanity checks to ensure the
    uploaded file resembles a PDF document. If validation passes, an expiry date
    one year from today is returned. Callers may persist the metadata for audit
    purposes and rely on the computed expiry date for follow-up reminders.
    """

    if not payload:
        raise ValueError("Uploaded document is empty.")
    if not payload.startswith(b"%PDF"):
        raise ValueError("Uploaded document is not a valid PDF.")

    expiry = datetime.now(UTC) + timedelta(days=365)
    return COIValidationResult(valid=True, expiry_date=expiry, errors=[])


__all__ = ["COIValidationResult", "validate_coi"]
