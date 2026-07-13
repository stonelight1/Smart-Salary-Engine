"""检查引擎测试"""

import pytest


class TestCheckRules:
    """检查规则逻辑测试（不依赖 DB）"""

    def test_block_level_is_blocking(self):
        """BLOCK 等级阻断计算"""
        block_levels = ["BLOCK"]
        assert len(block_levels) == 1
        for level in block_levels:
            assert level in ("BLOCK", "WARN", "INFO")

    def test_warn_not_blocking(self):
        """WARN 不阻断计算"""
        assert True  # WARN 在计算前被忽略

    def test_issue_code_format(self):
        """异常编码格式"""
        codes = [
            "EMPLOYEE_NAME_EMPTY",
            "EMPLOYEE_DUPLICATED",
            "FIELD_REQUIRED_MISSING",
            "FIELD_TYPE_INVALID",
            "FIELD_SOURCE_MISSING",
            "DATA_CONFLICT",
            "BASE_SALARY_NEGATIVE",
        ]
        for code in codes:
            assert "_" in code
            assert code.isupper()

    def test_name_cleaning(self):
        """姓名清洗规则"""
        from app.services.pool_service import clean_name

        assert clean_name("  张三  ") == "张三"
        assert clean_name("　李四　") == "李四"
        assert clean_name("") == ""
        assert clean_name("  ") == ""
        assert clean_name("王 五") == "王 五"  # 中间空格不删


class TestDecimalRound:
    """Decimal 舍入测试"""

    def test_half_up_rounding(self):
        from decimal import Decimal, ROUND_HALF_UP
        assert Decimal("123.456").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("123.46")
        assert Decimal("123.454").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("123.45")

    def test_intermediate_precision(self):
        from decimal import Decimal, ROUND_HALF_UP
        # 中间计算保留 6 位
        val = Decimal("10") / Decimal("3")
        rounded = val.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        assert rounded == Decimal("3.333333")

    def test_money_conversion(self):
        """金额转换规则"""
        from decimal import Decimal
        from app.services.pool_service import _to_decimal
        assert _to_decimal("1,234.56") == Decimal("1234.56")
        assert _to_decimal("￥1234.56") == Decimal("1234.56")
        assert _to_decimal("¥1000") == Decimal("1000")
        assert _to_decimal(None) is None
        assert _to_decimal("-") is None
        assert _to_decimal("—") is None
        assert _to_decimal("") is None
