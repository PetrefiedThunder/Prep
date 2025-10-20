import json
import pytest
from gaap_ledger_porter.core import GAAPLedgerPorter


def test_load_config_missing_file():
    porter = GAAPLedgerPorter()
    with pytest.raises(FileNotFoundError):
        porter.load_config("missing.json")


def test_validate_balanced_ledger():
    ledger = [
        {"debit": 100, "credit": 100},
        {"debit": 200, "credit": 200},
    ]
    porter = GAAPLedgerPorter()
    assert porter.validate(ledger) is True


def test_generate_report(tmp_path):
    ledger = [{"debit": 150, "credit": 150}]
    ledger_path = tmp_path / "ledger.json"
    with open(ledger_path, "w", encoding="utf-8") as handle:
        json.dump(ledger, handle)

    export_path = tmp_path / "report.txt"
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({
            "import_path": str(ledger_path),
            "export_path": str(export_path),
        }, handle)

    porter = GAAPLedgerPorter()
    porter.load_config(str(config_path))
    assert porter.validate() is True
    report = porter.generate_report()
    assert "Balanced: True" in report
    assert export_path.read_text() == report

def test_validate_unbalanced_ledger():
    ledger = [
        {"debit": 100, "credit": 50},
        {"debit": 25, "credit": 25},
    ]
    porter = GAAPLedgerPorter()
    assert porter.validate(ledger) is False


def test_generate_report_without_ledger():
    porter = GAAPLedgerPorter()
    with pytest.raises(ValueError):
        porter.generate_report()

