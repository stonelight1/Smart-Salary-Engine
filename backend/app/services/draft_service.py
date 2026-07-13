"""
工资草稿生成服务

负责：
- 基于上个月最终版生成本月工资草稿
- 继承基础信息（员工、工资标准等）
- 不继承月度结果（绩效、请假、考勤）
"""

import copy
import logging
import uuid
from datetime import datetime

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import (
    SalaryRun, EmployeeRecord, EmployeeFieldValue,
    AdjustmentItem, CheckIssue, ImportBatch,
)
from app.services.attendance_service import get_attendance_rule

logger = logging.getLogger(__name__)


def generate_draft_from_reference(
    target_run_id: str,
    created_by: str,
) -> dict:
    """
    从引用任务（上个月最终版）生成本月工资草稿。

    继承字段：
    - employee_name, employee_no, department, position
    - salary_standard (满绩效月薪标准)

    不继承：
    - performance_score (本月绩效得分)
    - leave_days (请假天数)
    - attendance_deduction (考勤扣款)
    - Adjustments (人工调整)
    - CheckIssues (异常)
    - CalcResults (计算结果)
    - 导入批次数据
    """
    db = SessionLocal()
    try:
        # 获取目标 run（本月草稿 DRAFT）
        target_run = db.query(SalaryRun).filter(SalaryRun.id == target_run_id).first()
        if not target_run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"目标任务不存在: {target_run_id}")
        if target_run.status not in ("CREATED",):
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"目标任务状态为「{target_run.status}」，仅 CREATED 状态可生成草稿",
            )

        # 获取引用 run（上月最终版）
        ref_run_id = target_run.reference_run_id
        if not ref_run_id:
            raise BizError(
                error_code="INVALID_ARGUMENT",
                message="目标任务未设置引用版本（reference_run_id 为空）",
            )

        ref_run = db.query(SalaryRun).filter(SalaryRun.id == ref_run_id).first()
        if not ref_run:
            raise BizError(
                error_code="RESOURCE_NOT_FOUND",
                message=f"引用版本不存在: {ref_run_id}",
            )
        if ref_run.run_version != "FINAL":
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message="引用版本不是最终版（FINAL），请先确认上月最终版",
            )

        # 获取上月员工列表
        ref_employees = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == ref_run_id,
            EmployeeRecord.status.in_(["NORMAL", "RESIGNED"]),
        ).all()

        copied_count = 0
        for ref_emp in ref_employees:
            # 跳过离职员工（RESIGNED）
            if ref_emp.status == "RESIGNED":
                continue

            # 创建新的员工记录
            new_emp_id = f"emp_{uuid.uuid4().hex[:8]}"
            new_emp = EmployeeRecord(
                id=new_emp_id,
                salary_run_id=target_run_id,
                employee_name=ref_emp.employee_name,
                status="NORMAL",
                # 继承基础信息
                employee_no=ref_emp.employee_no,
                department=ref_emp.department,
                position=ref_emp.position,
                # 继承工资标准
                salary_standard=ref_emp.salary_standard,
                basic_salary=ref_emp.basic_salary,
                performance_salary_standard=ref_emp.performance_salary_standard,
                # 绩效得分默认为空（本月等导入或默认 100%）
                performance_score=None,
                performance_score_source=None,
                performance_salary_actual=None,
                # 考勤重新计算
                attendance_rule_type=None,
                attendance_rule_name=None,
                standard_attendance_days=None,
                leave_days=None,
                actual_attendance_days=None,
                attendance_deduction=None,
                gross_salary_before_attendance=None,
            )
            db.add(new_emp)

            # 从 EmployeeFieldValue 继承工资标准相关字段
            ref_fields = db.query(EmployeeFieldValue).filter(
                EmployeeFieldValue.employee_record_id == ref_emp.id,
            ).all()

            inherit_codes = {"salary_standard", "employee_no", "department", "position"}
            for fv in ref_fields:
                if fv.field_code in inherit_codes:
                    new_fv = EmployeeFieldValue(
                        id=f"fv_{uuid.uuid4().hex[:8]}",
                        employee_record_id=new_emp_id,
                        field_code=fv.field_code,
                        value_text=fv.value_text,
                        value_decimal=fv.value_decimal,
                        value_type=fv.value_type,
                        source_file_id="draft_generated",
                        source_sheet="inherit",
                        source_row=0,
                        source_column=fv.field_code,
                        import_batch_id="",
                        is_manual=False,
                    )
                    db.add(new_fv)

            # 计算本月应出勤天数
            payroll_month = target_run.payroll_month
            dept = ref_emp.department or ""
            pos = ref_emp.position or ""
            rule = get_attendance_rule(dept, pos, payroll_month)
            new_emp.attendance_rule_type = rule["rule_type"]
            new_emp.attendance_rule_name = rule["rule_name"]
            new_emp.standard_attendance_days = rule["standard_attendance_days"]

            copied_count += 1

        # 更新任务状态
        target_run.status = "IMPORTED"
        db.commit()

        logger.info(
            "草稿生成完成: target=%s, ref=%s, employees=%d",
            target_run_id, ref_run_id, copied_count,
        )

        return {
            "status": "DRAFT",
            "reference_run_id": ref_run_id,
            "reference_month": ref_run.payroll_month,
            "employee_count": copied_count,
        }

    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("草稿生成异常: %s", str(e)[:300], exc_info=True)
        raise BizError(
            error_code="INTERNAL_ERROR",
            message=f"草稿生成失败: {str(e)}",
        )
    finally:
        db.close()
