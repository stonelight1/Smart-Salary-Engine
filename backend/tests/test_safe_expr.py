"""安全表达式引擎测试"""

from decimal import Decimal

import pytest

from app.engines.calculator.safe_expr import SafeExpr, SafeExprError


def make_expr(vars: dict | None = None) -> SafeExpr:
    return SafeExpr(vars or {})


class TestSafeExprArithmetic:
    def test_simple_addition(self):
        assert make_expr().evaluate("2 + 3") == Decimal("5")

    def test_simple_subtraction(self):
        assert make_expr().evaluate("10 - 3") == Decimal("7")

    def test_multiplication(self):
        assert make_expr().evaluate("4 * 5") == Decimal("20")

    def test_division(self):
        assert make_expr().evaluate("10 / 4") == Decimal("2.5")

    def test_parentheses(self):
        assert make_expr().evaluate("(2 + 3) * 4") == Decimal("20")

    def test_complex_expression(self):
        assert make_expr().evaluate("2 + 3 * 4 - 6 / 2") == Decimal("11")

    def test_decimal_precision(self):
        assert make_expr().evaluate("0.1 + 0.2") == Decimal("0.30")


class TestSafeExprVariables:
    def test_variable_lookup(self):
        se = make_expr({"base": "8000", "bonus": "1000"})
        assert se.evaluate("base") == Decimal("8000")

    def test_variable_expression(self):
        se = make_expr({"base": "8000", "bonus": "1000"})
        assert se.evaluate("base + bonus") == Decimal("9000")

    def test_mixed_vars_and_numbers(self):
        se = make_expr({"base": "8000"})
        assert se.evaluate("base + 500") == Decimal("8500")


class TestSafeExprFunctions:
    def test_if_null_with_value(self):
        assert make_expr().evaluate("if_null(100, 0)") == Decimal("100")

    def test_if_null_with_none(self):
        assert make_expr({"x": None}).evaluate("if_null(x, 0)") == Decimal("0")

    def test_sum_values(self):
        assert make_expr().evaluate("sum_values(100, 200, 300)") == Decimal("600")

    def test_max_value(self):
        assert make_expr().evaluate("max_value(10, 20, 5)") == Decimal("20")

    def test_min_value(self):
        assert make_expr().evaluate("min_value(10, 20, 5)") == Decimal("5")

    def test_round_money(self):
        result = make_expr().evaluate("round_money(123.456, 2)")
        assert result == Decimal("123.46")

    def test_nested_function(self):
        expr = "sum_values(if_null(a, 0), if_null(b, 0))"
        se = make_expr({"a": "100"})
        assert se.evaluate(expr) == Decimal("100")

    def test_case_when_true(self):
        assert make_expr().evaluate("case_when(True, 10, 20)") == Decimal("10")

    def test_case_when_false(self):
        assert make_expr().evaluate("case_when(False, 10, 20)") == Decimal("20")


class TestSafeExprSecurity:
    def test_eval_blocked(self):
        with pytest.raises(SafeExprError):
            make_expr().evaluate('__import__("os").system("ls")')

    def test_exec_blocked(self):
        with pytest.raises(SafeExprError):
            make_expr().evaluate('exec("print(1)")')

    def test_import_blocked(self):
        with pytest.raises(SafeExprError):
            make_expr().evaluate('import_()')

    def test_invalid_characters(self):
        with pytest.raises(SafeExprError):
            make_expr().evaluate("exec('ls')")

    def test_unknown_function_blocked(self):
        with pytest.raises(SafeExprError):
            make_expr().evaluate("unknown_func(1, 2, 3)")


class TestSafeExprFullFormula:
    """模拟完整工资公式计算"""

    def test_gross_salary(self):
        vars = {
            "base_salary": Decimal("8000"),
            "performance_bonus": Decimal("1000"),
            "allowance_total": Decimal("300"),
            "attendance_deduction": Decimal("0"),
        }
        se = SafeExpr(vars)
        result = se.evaluate("base_salary + performance_bonus + allowance_total - attendance_deduction")
        assert result == Decimal("9300")

    def test_net_salary(self):
        vars = {
            "gross_salary": Decimal("9300"),
            "deduction_total": Decimal("700"),
        }
        se = SafeExpr(vars)
        result = se.evaluate("gross_salary - deduction_total")
        assert result == Decimal("8600")

    def test_deduction_total(self):
        vars = {
            "other_deduction": Decimal("100"),
            "social_security_personal": Decimal("400"),
            "housing_fund_personal": Decimal("200"),
        }
        se = SafeExpr(vars)
        result = se.evaluate("other_deduction + social_security_personal + housing_fund_personal")
        assert result == Decimal("700")

    def test_salary_comparison(self):
        se = make_expr({"net_salary": "50000"})
        assert se.evaluate("net_salary <= 100000") is True
        assert se.evaluate("net_salary > 200000") is False

    def test_negative_check(self):
        se = make_expr({"base_salary": "-100"})
        assert se.evaluate("base_salary >= 0") is False
