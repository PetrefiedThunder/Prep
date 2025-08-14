from hbs_model_validator.core import HBSModelValidator


def test_methods_return_none():
    validator = HBSModelValidator()
    assert validator.load_config('dummy_path') is None
    assert validator.validate({}) is None
    assert validator.generate_report() is None
