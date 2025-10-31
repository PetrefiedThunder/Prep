"""Utilities for validating certificate of insurance (COI) documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import List


@dataclass(slots=True)
class COIValidationResult:
    """Result of a COI validation attempt."""

    valid: bool
    expiry_date: datetime | None
    errors: List[str]
    warnings: List[str] = field(default_factory=list)


def validate_coi(payload: bytes, *, pilot_mode: bool = False) -> COIValidationResult:
    """Validate the uploaded COI PDF payload.

    The current implementation performs lightweight sanity checks to ensure the
    uploaded file resembles a PDF document. If validation passes, an expiry date
    one year from today is returned. Callers may persist the metadata for audit
    purposes and rely on the computed expiry date for follow-up reminders.
    """

    errors: List[str] = []
    warnings: List[str] = []

    if not payload:
        message = "Uploaded document is empty."
        if pilot_mode:
            warnings.append(message)
        else:
            raise ValueError(message)

    if payload and not payload.startswith(b"%PDF"):
        message = "Uploaded document is not a valid PDF."
        if pilot_mode:
            warnings.append(message)
        else:
            raise ValueError(message)

    is_valid = not warnings and not errors
    expiry = datetime.now(UTC) + timedelta(days=365) if is_valid else None

    return COIValidationResult(
        valid=is_valid,
        expiry_date=expiry,
        errors=errors,
        warnings=warnings,
    )


__all__ = ["COIValidationResult", "validate_coi"]
