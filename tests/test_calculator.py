import pytest

from anka.tools.calculator import CalculationError, evaluate_expression


def test_allowed_math_works():
    assert evaluate_expression("2 + 3 * 4") == 14
    assert evaluate_expression("pi * 2") > 6


@pytest.mark.parametrize("expression", ["__import__('os').system('x')", "open('x')", "(1).__class__"])
def test_code_is_not_an_expression(expression):
    with pytest.raises(CalculationError):
        evaluate_expression(expression)


def test_extreme_power_is_rejected():
    with pytest.raises(CalculationError):
        evaluate_expression("2 ** 101")
