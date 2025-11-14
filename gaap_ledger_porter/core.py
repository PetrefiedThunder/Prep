from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from prep.utility.config_schema import BaseConfigSchema, IterableValidationMixin


class GAAPLedgerPorter(IterableValidationMixin, BaseConfigSchema):
    """Handles export and import of GAAP compliant ledgers."""

    def __init__(self, *, logger=None) -> None:
        super().__init__(logger=logger, config_required=False)
        self.ledger: list[dict[str, float]] = []
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:  # type: ignore[override]
        super().load_config(config_path)
        import_path = self.config.get("import_path")
        if import_path:
            path = Path(import_path)
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, list):
                raise TypeError("Ledger import must be a list of entries")
            self.ledger = self._ensure_list(data)

    def validate(self, ledger: Iterable[dict[str, float]] | None = None) -> bool:  # type: ignore[override]
        if ledger is None and not self.ledger:
            raise ValueError("Ledger data not provided")
        return super().validate(ledger if ledger is not None else self.ledger)

    def _run_validation(self, ledger: Iterable[dict[str, Any]]) -> list[str]:  # type: ignore[override]
        ledger_list = self._ensure_list(ledger)
        errors: list[str] = []
        total_debit = 0.0
        total_credit = 0.0

        for index, entry in enumerate(ledger_list):
            missing = {"debit", "credit"} - set(entry)
            if missing:
                errors.append(
                    f"Entry {index} missing required fields: {', '.join(sorted(missing))}"
                )
                continue

            debit = entry["debit"]
            credit = entry["credit"]
            if not isinstance(debit, (int, float)) or not isinstance(credit, (int, float)):
                errors.append(f"Entry {index} has non-numeric debit/credit values")
                continue

            total_debit += float(debit)
            total_credit += float(credit)

        balanced = abs(total_debit - total_credit) <= 1e-6
        self.is_valid = not errors and balanced
        self.ledger = ledger_list

        if not balanced:
            errors.append(f"Ledger is not balanced: debit={total_debit}, credit={total_credit}")

        return errors

    def generate_report(self) -> str:  # type: ignore[override]
        if not self.ledger:
            raise ValueError("Ledger data not loaded")

        if not self._validated:
            self.validate(self.ledger)

        if self.validation_errors:
            return super().generate_report()

        total_debit = sum(float(entry["debit"]) for entry in self.ledger)
        total_credit = sum(float(entry["credit"]) for entry in self.ledger)
        report = (
            f"Total Debit: {total_debit}, Total Credit: {total_credit}, Balanced: {self.is_valid}"
        )

        export_path = self.config.get("export_path")
        if export_path:
            path = Path(export_path)
            path.write_text(report, encoding="utf-8")

        return report
