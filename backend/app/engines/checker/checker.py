"""数据检查引擎

执行 BLOCK/WARN/INFO 三级异常检查
"""

from decimal import Decimal
from typing import Any

from app.db.database import SessionLocal
from app.models import (
    SalaryRun, EmployeeRecord, EmployeeFieldValue, CheckIssue,
    SheetMapping, ColumnMapping, ImportBatch,
)

from app.core.config import config_loader


def run_checks(salary_run_id: str) -> dict[str, int]:
    """对指定任务执行所有数据检查"""
    db = SessionLocal()
    try:
        # 清空旧的未处理自动异常
        old_open = db.query(CheckIssue).filter(
            CheckIssue.salary_run_id == salary_run_id,
            CheckIssue.status == "OPEN",
        ).all()
        for issue in old_open:
            db.delete(issue)
        db.commit()

        issues: list[CheckIssue] = []

        # 1. 员工检查
        _check_employees(db, salary_run_id, issues)

        # 2. 字段检查
        _check_fields(db, salary_run_id, issues)

        # 3. 数据冲突检查
        _check_data_conflicts(db, salary_run_id, issues)

        # 保存异常
        for issue in issues:
            db.add(issue)
        db.commit()

        # 统计
        block_count = sum(1 for i in issues if i.level == "BLOCK")
        warn_count = sum(1 for i in issues if i.level == "WARN")
        info_count = sum(1 for i in issues if i.level == "INFO")

        # 更新任务状态
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if run:
            if block_count > 0:
                run.status = "CHECK_FAILED"
            else:
                run.status = "CHECK_PASSED"
            db.commit()

        return {
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": info_count,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def _make_issue(
    salary_run_id: str,
    issue_code: str,
    level: str,
    message: str,
    employee_record_id: str | None = None,
    field_code: str | None = None,
) -> CheckIssue:
    import uuid
    return CheckIssue(
        id=f"issue_{uuid.uuid4().hex[:8]}",
        salary_run_id=salary_run_id,
        employee_record_id=employee_record_id,
        issue_code=issue_code,
        level=level,
        field_code=field_code,
        message=message,
        status="OPEN",
    )


def _check_employees(
    db: SessionLocal,
    salary_run_id: str,
    issues: list[CheckIssue],
):
    """员工检查"""
    employees = db.query(EmployeeRecord).filter(
        EmployeeRecord.salary_run_id == salary_run_id,
    ).all()

    for emp in employees:
        # 姓名为空检查
        if not emp.employee_name.strip():
            issues.append(_make_issue(
                salary_run_id, "EMPLOYEE_NAME_EMPTY", "BLOCK",
                f"员工姓名为空（ID: {emp.id}）",
                employee_record_id=emp.id,
                field_code="employee_name",
            ))

        # 重名状态检查
        if emp.status == "NAME_DUPLICATE":
            issues.append(_make_issue(
                salary_run_id, "EMPLOYEE_DUPLICATED", "BLOCK",
                f"存在同名员工: {emp.employee_name}，请检查 Excel 后重新导入",
                employee_record_id=emp.id,
                field_code="employee_name",
            ))


def _check_fields(
    db: SessionLocal,
    salary_run_id: str,
    issues: list[CheckIssue],
):
    """字段检查"""
    employees = db.query(EmployeeRecord).filter(
        EmployeeRecord.salary_run_id == salary_run_id,
    ).all()

    fields_cfg = config_loader.get("fields") or {}
    field_defs = fields_cfg.get("fields", {})

    for emp in employees:
        existing_fields = {
            fv.field_code: fv
            for fv in db.query(EmployeeFieldValue).filter(
                EmployeeFieldValue.employee_record_id == emp.id,
            ).all()
        }

        for field_code, field_info in field_defs.items():
            is_required = field_info.get("required", False)
            field_type = field_info.get("type", "string")
            fv = existing_fields.get(field_code)

            # 必填字段检查
            if is_required and not fv:
                issues.append(_make_issue(
                    salary_run_id, "FIELD_REQUIRED_MISSING", "BLOCK",
                    f"{emp.employee_name} 缺少{field_info.get('name')}，无法计算工资",
                    employee_record_id=emp.id,
                    field_code=field_code,
                ))
                continue

            # 可选字段缺失提醒（不静默补 0）
            if not is_required and not fv and field_type in ("money", "number"):
                issues.append(_make_issue(
                    salary_run_id, "FIELD_OPTIONAL_MISSING", "WARN",
                    f"{emp.employee_name} 的{field_info.get('name')}未填写，请确认是否按 0 计算",
                    employee_record_id=emp.id,
                    field_code=field_code,
                ))
                continue

            if not fv:
                continue

            # 金额格式检查
            if field_type == "money":
                if fv.value_decimal is None and fv.value_text:
                    # 尝试解析
                    try:
                        Decimal(str(fv.value_text).replace(",", "").replace("￥", "").strip())
                    except Exception:
                        issues.append(_make_issue(
                            salary_run_id, "FIELD_TYPE_INVALID", "BLOCK",
                            f"{emp.employee_name} 的{field_info.get('name')}金额格式非法: {fv.value_text}",
                            employee_record_id=emp.id,
                            field_code=field_code,
                        ))

                # 负金额检查
                if fv.value_decimal is not None and fv.value_decimal < Decimal("0"):
                    level = "BLOCK" if field_code == "base_salary" else "WARN"
                    issues.append(_make_issue(
                        salary_run_id, f"{field_code.upper()}_NEGATIVE", level,
                        f"{emp.employee_name} 的{field_info.get('name')}为负: {fv.value_decimal}",
                        employee_record_id=emp.id,
                        field_code=field_code,
                    ))

        # 来源丢失检查
        for field_code, fv in existing_fields.items():
            if not fv.source_file_id or fv.source_file_id == "manual":
                continue
            if not fv.import_batch_id:
                issues.append(_make_issue(
                    salary_run_id, "FIELD_SOURCE_MISSING", "BLOCK",
                    f"{emp.employee_name} 的字段 {field_code} 来源丢失",
                    employee_record_id=emp.id,
                    field_code=field_code,
                ))


def _check_data_conflicts(
    db: SessionLocal,
    salary_run_id: str,
    issues: list[CheckIssue],
):
    """检查已生成的数据冲突异常"""
    # 数据冲突已经在导入时生成，这里做补充检查
    employees = db.query(EmployeeRecord).filter(
        EmployeeRecord.salary_run_id == salary_run_id,
    ).all()

    for emp in employees:
        # 检查同一个字段是否有多个不同来源的值（通过现有冲突 issue 来判定）
        existing_conflicts = db.query(CheckIssue).filter(
            CheckIssue.employee_record_id == emp.id,
            CheckIssue.issue_code == "DATA_CONFLICT",
            CheckIssue.status == "OPEN",
        ).count()

        if existing_conflicts > 0:
            issues.append(_make_issue(
                salary_run_id, "DATA_CONFLICT", "BLOCK",
                f"{emp.employee_name} 存在 {existing_conflicts} 个字段数据冲突",
                employee_record_id=emp.id,
            ))
