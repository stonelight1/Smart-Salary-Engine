"""
考勤规则服务

根据员工部门、岗位和工资月份确定应出勤天数。

规则：
1. 岗位为客服/主播，或部门为产品部门 → 按自然月天数计算
2. 其他员工 → 固定 21.75 天
"""

from calendar import monthrange
from decimal import Decimal


# 特殊岗位关键词
SPECIAL_POSITIONS = ["客服", "主播"]
# 特殊部门关键词
SPECIAL_DEPARTMENTS = ["产品"]

# 自然月天数 → 应出勤天数映射
MONTH_DAYS_MAP = {
    31: Decimal("27"),
    30: Decimal("26"),
    29: Decimal("26"),
    28: Decimal("26"),
}

# 普通员工应出勤天数
DEFAULT_ATTENDANCE_DAYS = Decimal("21.75")


def get_attendance_rule(
    department: str | None,
    position: str | None,
    payroll_month: str,
) -> dict:
    """
    根据员工部门、岗位和工资月份计算应出勤天数和考勤规则。

    Args:
        department: 部门
        position: 岗位
        payroll_month: 工资月份 YYYY-MM

    Returns:
        {
            "rule_type": "NORMAL" | "SPECIAL",
            "rule_name": str,
            "standard_attendance_days": Decimal,
        }
    """
    # 1. 检查是否命中特殊规则
    is_special = False
    rule_name = "标准21.75天"

    if position:
        pos_lower = position.strip().lower()
        for sp in SPECIAL_POSITIONS:
            if sp.lower() in pos_lower:
                is_special = True
                rule_name = f"岗位[{position}]适用特殊考勤规则"
                break

    if not is_special and department:
        dept_lower = department.strip().lower()
        for sd in SPECIAL_DEPARTMENTS:
            if sd.lower() in dept_lower:
                is_special = True
                rule_name = f"部门[{department}]适用特殊考勤规则"
                break

    if not is_special and position:
        pos_lower = position.strip().lower()
        for sp in SPECIAL_POSITIONS:
            if sp in pos_lower:
                is_special = True
                rule_name = f"岗位[{position}]适用特殊考勤规则"
                break

    # 2. 计算应出勤天数
    if is_special:
        year, month = payroll_month.split("-")
        days_in_month = monthrange(int(year), int(month))[1]
        standard_days = MONTH_DAYS_MAP.get(days_in_month, DEFAULT_ATTENDANCE_DAYS)
        rule_type = "SPECIAL"
    else:
        standard_days = DEFAULT_ATTENDANCE_DAYS
        rule_type = "NORMAL"

    return {
        "rule_type": rule_type,
        "rule_name": rule_name,
        "standard_attendance_days": standard_days,
    }


def calculate_leave_summary(leave_records: list) -> Decimal:
    """
    汇总员工本月请假总天数。
    leave_records: 请假记录列表，每项包含 leave_days 字段
    """
    total = Decimal("0")
    for rec in leave_records:
        if hasattr(rec, "leave_days"):
            total += Decimal(str(rec.leave_days))
        elif isinstance(rec, dict):
            total += Decimal(str(rec.get("leave_days", 0)))
    return total
