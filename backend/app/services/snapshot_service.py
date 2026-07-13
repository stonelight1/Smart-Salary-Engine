"""
月度工资快照服务

从员工档案生成月度工资快照：
1. 获取本月在职员工
2. 获取本月生效的薪资标准
3. 初始化绩效/请假/考勤
4. 计算应出勤天数
5. 生成快照
"""

import logging
import uuid
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import (
    EmployeeMaster, SalaryStandard, SalaryRun,
    MonthlySalarySnapshot, SalaryItemDetail,
)
from app.services.attendance_service import get_attendance_rule

logger = logging.getLogger(__name__)


def generate_monthly_snapshots(salary_run_id: str, created_by: str) -> dict:
    """
    从员工档案生成本月工资快照。
    在创建工资任务时自动调用。
    """
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        year, month = run.payroll_month.split("-")
        y, m = int(year), int(month)
        month_start = date(y, m, 1)
        _, days_in_month = monthrange(y, m)
        month_end = date(y, m, days_in_month)

        # 获取本月在职员工
        actives = db.query(EmployeeMaster).filter(
            EmployeeMaster.status == "ACTIVE",
        ).all()

        new_hire_count = 0
        resign_count = 0
        snapshot_count = 0

        for emp in actives:
            # 入职日期 <= 当月最后一天
            if emp.hire_date and emp.hire_date > month_end:
                continue
            # 离职日期为空或 >= 当月第一天
            if emp.resign_date and emp.resign_date < month_start:
                continue

            # 获取本月生效的薪资标准
            ss = db.query(SalaryStandard).filter(
                SalaryStandard.employee_master_id == emp.id,
                SalaryStandard.end_date.is_(None),
            ).first()

            salary_std = ss.salary_standard if ss else Decimal("0")
            basic_salary = ss.basic_salary if ss else (salary_std * Decimal("0.70"))
            perf_salary_std = ss.performance_salary_standard if ss else (salary_std * Decimal("0.30"))

            # 计算应出勤天数
            dept = emp.department or ""
            pos = emp.position or ""
            rule = get_attendance_rule(dept, pos, run.payroll_month)

            # 入职/离职当月按剩余天数折算
            if emp.hire_date and emp.hire_date > month_start:
                new_hire_count += 1
            if emp.resign_date and emp.resign_date <= month_end:
                resign_count += 1

            snap_id = f"snap_{uuid.uuid4().hex[:8]}"
            snap = MonthlySalarySnapshot(
                id=snap_id,
                salary_run_id=salary_run_id,
                employee_master_id=emp.id,
                employee_no=emp.employee_no or "",
                employee_name=emp.employee_name,
                department=dept,
                position=pos,
                salary_standard=salary_std,
                basic_salary=basic_salary,
                performance_salary_standard=perf_salary_std,
                performance_score=Decimal("1.0"),
                performance_score_source="DEFAULT",
                performance_salary_actual=None,
                attendance_rule_type=rule["rule_type"],
                attendance_rule_name=rule["rule_name"],
                standard_attendance_days=rule["standard_attendance_days"],
                leave_days=Decimal("0"),
                actual_attendance_days=None,
                attendance_deduction=None,
                gross_salary_before_attendance=None,
                gross_salary_after_attendance=None,
                net_salary=None,
                status="ACTIVE",
                created_by=created_by,
            )
            db.add(snap)
            snapshot_count += 1

        # 更新任务统计
        run.employee_count = snapshot_count
        run.new_hire_count = new_hire_count
        run.resign_count = resign_count
        run.status = "DRAFT"
        db.commit()

        logger.info(
            "月度快照生成: run=%s, month=%s, employees=%d, new=%d, resign=%d",
            salary_run_id, run.payroll_month, snapshot_count, new_hire_count, resign_count,
        )

        return {
            "employee_count": snapshot_count,
            "new_hire_count": new_hire_count,
            "resign_count": resign_count,
        }
    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("快照生成失败: %s", str(e)[:300], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="生成本月工资快照失败")
    finally:
        db.close()


def calculate_snapshot_salary(snapshot_id: str) -> dict:
    """
    计算单个快照的工资（基于快照数据，非实时档案）。

    公式链:
    basic_salary = salary_standard * 0.70  (已在快照中)
    performance_salary_standard = salary_standard * 0.30 (已在快照中)
    performance_salary_actual = performance_salary_standard * performance_score
    gross_before = basic_salary + performance_salary_actual
    deduction = gross_before / standard_days * leave_days
    gross_after = gross_before - deduction
    """
    db = SessionLocal()
    try:
        snap = db.query(MonthlySalarySnapshot).filter(
            MonthlySalarySnapshot.id == snapshot_id
        ).first()
        if not snap:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="快照不存在")

        TWO_PLACES = Decimal("0.01")
        EIGHT_PLACES = Decimal("0.00000001")

        ss = snap.salary_standard or Decimal("0")
        basic = snap.basic_salary or (ss * Decimal("0.70"))
        perf_std = snap.performance_salary_standard or (ss * Decimal("0.30"))
        score = snap.performance_score or Decimal("1.0")

        # 实际绩效工资
        perf_actual = (perf_std * score).quantize(EIGHT_PLACES, rounding=ROUND_HALF_UP)

        # 考勤前应发
        gross_before = (basic + perf_actual).quantize(EIGHT_PLACES, rounding=ROUND_HALF_UP)

        # 考勤扣款
        std_days = snap.standard_attendance_days or Decimal("21.75")
        leave = snap.leave_days or Decimal("0")
        if leave > 0:
            deduction = (gross_before / std_days * leave).quantize(EIGHT_PLACES, rounding=ROUND_HALF_UP)
        else:
            deduction = Decimal("0")

        # 考勤后工资
        gross_after = (gross_before - deduction).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # 获取工资项目明细
        items = db.query(SalaryItemDetail).filter(
            SalaryItemDetail.snapshot_id == snapshot_id,
        ).all()
        extra_earnings = sum(i.amount for i in items if i.item_type == "EARNING")
        extra_deductions = sum(i.amount for i in items if i.item_type == "DEDUCTION")
        company_costs = sum(i.amount for i in items if i.item_type == "COMPANY_COST")

        # 应发 = 考勤后 + 额外收入
        total_earnings = gross_after + extra_earnings
        # 扣款 = 考勤扣款 + 额外扣款
        total_deductions = deduction + extra_deductions
        # 实发
        net = (total_earnings - total_deductions).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # 更新快照
        snap.performance_salary_actual = perf_actual.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        snap.gross_salary_before_attendance = gross_before.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        snap.attendance_deduction = deduction.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        snap.gross_salary_after_attendance = gross_after
        snap.actual_attendance_days = std_days - leave
        snap.net_salary = net
        db.commit()

        return {
            "snapshot_id": snapshot_id,
            "employee_name": snap.employee_name,
            "basic_salary": float(basic),
            "perf_actual": float(perf_actual),
            "gross_before": float(gross_before),
            "deduction": float(deduction),
            "gross_after": float(gross_after),
            "extra_earnings": float(extra_earnings),
            "extra_deductions": float(extra_deductions),
            "net_salary": float(net),
        }
    except BizError:
        raise
    except Exception as e:
        logger.error("快照计算失败 %s: %s", snapshot_id, str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="工资计算失败")
    finally:
        db.close()


def add_salary_item(snapshot_id: str, item_type: str, item_code: str, item_name: str,
                    amount: Decimal, source: str = "SYSTEM", remark: str = "") -> dict:
    """添加工资项目明细"""
    db = SessionLocal()
    try:
        snap = db.query(MonthlySalarySnapshot).filter(
            MonthlySalarySnapshot.id == snapshot_id
        ).first()
        if not snap:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="快照不存在")

        item = SalaryItemDetail(
            id=f"si_{uuid.uuid4().hex[:8]}",
            snapshot_id=snapshot_id,
            salary_run_id=snap.salary_run_id,
            item_type=item_type,
            item_code=item_code,
            item_name=item_name,
            amount=amount,
            source=source,
            remark=remark,
        )
        db.add(item)
        db.commit()
        return {"id": item.id, "amount": float(amount)}
    finally:
        db.close()


def list_snapshots(run_id: str, page: int = 1, page_size: int = 20) -> dict:
    """查询月度快照列表"""
    db = SessionLocal()
    try:
        query = db.query(MonthlySalarySnapshot).filter(
            MonthlySalarySnapshot.salary_run_id == run_id,
            MonthlySalarySnapshot.status == "ACTIVE",
        )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for s in items:
            detail_items = db.query(SalaryItemDetail).filter(
                SalaryItemDetail.snapshot_id == s.id,
            ).all()
            result.append({
                "id": s.id,
                "employee_no": s.employee_no or "",
                "employee_name": s.employee_name,
                "department": s.department or "",
                "position": s.position or "",
                "salary_standard": float(s.salary_standard) if s.salary_standard else 0,
                "basic_salary": float(s.basic_salary) if s.basic_salary else 0,
                "performance_salary_standard": float(s.performance_salary_standard) if s.performance_salary_standard else 0,
                "performance_score": float(s.performance_score) if s.performance_score else 1.0,
                "performance_salary_actual": float(s.performance_salary_actual) if s.performance_salary_actual else 0,
                "standard_attendance_days": float(s.standard_attendance_days) if s.standard_attendance_days else 0,
                "leave_days": float(s.leave_days) if s.leave_days else 0,
                "actual_attendance_days": float(s.actual_attendance_days) if s.actual_attendance_days else 0,
                "attendance_deduction": float(s.attendance_deduction) if s.attendance_deduction else 0,
                "gross_salary_before_attendance": float(s.gross_salary_before_attendance) if s.gross_salary_before_attendance else 0,
                "gross_salary_after_attendance": float(s.gross_salary_after_attendance) if s.gross_salary_after_attendance else 0,
                "net_salary": float(s.net_salary) if s.net_salary else 0,
                "items": [
                    {"code": i.item_code, "name": i.item_name, "type": i.item_type, "amount": float(i.amount)}
                    for i in detail_items
                ],
            })
        return {"items": result, "total": total}
    finally:
        db.close()
