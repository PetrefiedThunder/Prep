import json
from typing import Any, Dict, Iterable, Optional


class GAAPLedgerPorter:
    """Handles export and import of GAAP compliant ledgers."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.ledger: Iterable[Dict[str, float]] = []
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:
        """Load ledger porting configuration.

        The configuration is expected to be a JSON document containing
        ``import_path`` and optionally ``export_path`` values. When an
        ``import_path`` is supplied the ledger data will be loaded from that
        file immediately.
        """

        with open(config_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)

        import_path = self.config.get("import_path")
        if import_path:
            with open(import_path, "r", encoding="utf-8") as handle:
                self.ledger = json.load(handle)

    def validate(self, ledger: Optional[Iterable[Dict[str, float]]] = None) -> bool:
        """Validate ledger entries against GAAP requirements.

        Each ledger entry must contain numeric ``debit`` and ``credit`` keys and
        the totals for each side must balance.
        """

        ledger_to_check = ledger if ledger is not None else self.ledger

        total_debit = 0.0
        total_credit = 0.0
        for entry in ledger_to_check:
            if not {"debit", "credit"}.issubset(entry):
                self.is_valid = False
                return False

            debit = entry["debit"]
            credit = entry["credit"]
            if not isinstance(debit, (int, float)) or not isinstance(credit, (int, float)):
                self.is_valid = False
                return False

            total_debit += float(debit)
            total_credit += float(credit)

        self.is_valid = total_debit == total_credit
        return self.is_valid

    def generate_report(self) -> str:
        """Produce a summary of ledger compliance.

        The generated report is returned as a string. If an ``export_path`` is
        configured it will also be written to that file.
        """

        if not self.ledger:
            raise ValueError("Ledger data not loaded")

        balanced = self.validate()

        total_debit = sum(entry["debit"] for entry in self.ledger)
        total_credit = sum(entry["credit"] for entry in self.ledger)
        report = (
            f"Total Debit: {total_debit}, Total Credit: {total_credit}, "
            f"Balanced: {balanced}"
        )

        export_path = self.config.get("export_path")
        if export_path:
            with open(export_path, "w", encoding="utf-8") as handle:
                handle.write(report)

        return report
