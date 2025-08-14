from gaap_ledger_porter.core import GAAPLedgerPorter


def test_methods_return_none():
    porter = GAAPLedgerPorter()
    assert porter.load_config('dummy_path') is None
    assert porter.validate({}) is None
    assert porter.generate_report() is None
