"""Salary Run 服务"""

import json
import uuid
from datetime import datetime

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import (
    SalaryRun, ImportBatch, EmployeeRecord, CalculationResult,
    ExportFile, CheckIssue, AdjustmentItem,
)


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def create_run(name: str, payroll_month: str, remark: str | None, created_by: str, reference_run_id: str | None = None, run_version: str = "DRAFT", reference_source_type: str = "SYSTEM_FINAL", reference_external_id: str | None = None) -> dict:
    """创建工资核算任务"""
    db = SessionLocal()
    try:
        existing = db.query(SalaryRun).filter(SalaryRun.name == name, SalaryRun.delete_flag == 0).first()
        if existing:
            raise BizError(
                error_code="INVALID_ARGUMENT",
                message=f"任务名称已存在: {name}",
            )
        run_id = generate_id("run_")
        run = SalaryRun(
            id=run_id,
            name=name,
            payroll_month=payroll_month,
            status="CREATED",
            remark=remark or "",
            created_by=created_by,
            reference_run_id=reference_run_id or "",
            reference_source_type=reference_source_type,
            reference_external_id=reference_external_id,
            run_version=run_version,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return _run_to_dict(run)
    finally:
        db.close()


def list_runs(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    include_archived: bool = False,
) -> dict:
    """查询任务列表（默认排除已删除和已归档）"""
    db = SessionLocal()
    try:
        query = db.query(SalaryRun).filter(SalaryRun.delete_flag == 0)
        if not include_archived:
            query = query.filter(SalaryRun.archive_flag == 0)
        query = query.order_by(SalaryRun.created_at.desc())
        if keyword:
            query = query.filter(SalaryRun.name.contains(keyword))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [_run_to_dict(r) for r in items],
            "total": total,
        }
    finally:
        db.close()


def get_run(run_id: str) -> dict:
    """查询任务详情（已删除任务返回不存在）"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id).first()
        if not run or run.delete_flag == 1:
            raise BizError(
                error_code="RESOURCE_NOT_FOUND",
                message=f"任务不存在: {run_id}",
            )
        return _run_to_dict(run)
    finally:
        db.close()


def confirm_run(run_id: str, confirmed_by: str) -> dict:
    """确认任务"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")
        if run.status != "CALCULATED":
            raise BizError(error_code="RUN_STATUS_NOT_ALLOWED", message="仅已核算的任务可以确认")
        run.status = "CONFIRMED"
        db.commit()
        return _run_to_dict(run)
    finally:
        db.close()


def lock_run(run_id: str, reason: str, locked_by: str) -> dict:
    """锁定任务"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")
        if run.status != "CONFIRMED":
            raise BizError(error_code="RUN_STATUS_NOT_ALLOWED", message="仅已确认的任务可以锁定")
        run.status = "LOCKED"
        db.commit()
        return _run_to_dict(run)
    finally:
        db.close()


def unlock_run(run_id: str, reason: str, unlocked_by: str) -> dict:
    """解锁任务"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")
        if run.status != "LOCKED":
            raise BizError(error_code="RUN_STATUS_NOT_ALLOWED", message="仅已锁定的任务可以解锁")
        run.status = "CONFIRMED"
        db.commit()
        return _run_to_dict(run)
    finally:
        db.close()


def _check_business_data(db: SessionLocal, run_id: str) -> dict:
    """检查任务是否关联了业务数据，返回检查结果"""
    emp_count = db.query(EmployeeRecord).filter(EmployeeRecord.salary_run_id == run_id).count()
    batch_count = db.query(ImportBatch).filter(ImportBatch.salary_run_id == run_id).count()
    calc_version = db.query(SalaryRun).filter(SalaryRun.id == run_id).first().current_calc_version
    calc_count = db.query(CalculationResult).filter(CalculationResult.salary_run_id == run_id).count()
    issue_count = db.query(CheckIssue).filter(CheckIssue.salary_run_id == run_id).count()
    export_count = db.query(ExportFile).filter(ExportFile.salary_run_id == run_id).count()
    adj_count = db.query(AdjustmentItem).filter(AdjustmentItem.salary_run_id == run_id).count()

    return {
        "has_employees": emp_count > 0,
        "has_batches": batch_count > 0,
        "has_calc_version": calc_version > 0,
        "has_calc_results": calc_count > 0,
        "has_issues": issue_count > 0,
        "has_exports": export_count > 0,
        "has_adjustments": adj_count > 0,
        "has_business_data": (
            emp_count > 0 or batch_count > 0 or calc_version > 0
            or calc_count > 0 or export_count > 0 or adj_count > 0
        ),
    }


def delete_run(run_id: str, deleted_by: str) -> dict:
    """软删除任务（仅允许空任务删除）"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")

        # 校验状态
        if run.status not in ("CREATED",):
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"任务当前状态为「{run.status}」，不允许删除，请使用作废功能",
            )

        # 校验业务数据
        biz = _check_business_data(db, run_id)
        if biz["has_business_data"]:
            if biz["has_employees"]:
                raise BizError(error_code="HAS_BUSINESS_DATA", message="该任务已存在员工数据，不能删除，请使用作废")
            if biz["has_calc_version"]:
                raise BizError(error_code="HAS_BUSINESS_DATA", message="该任务已产生计算版本，不能删除，请使用作废")
            if biz["has_exports"]:
                raise BizError(error_code="HAS_BUSINESS_DATA", message="该任务已导出工资表，不能删除")
            raise BizError(error_code="HAS_BUSINESS_DATA", message="该任务已存在业务数据，不能删除，请使用作废")

        # 执行软删除
        now = datetime.now()
        run.delete_flag = 1
        run.deleted_by = deleted_by
        run.deleted_at = now
        db.commit()

        return _run_to_dict(run)
    finally:
        db.close()


def void_run(run_id: str, reason: str, voided_by: str) -> dict:
    """作废任务"""
    if not reason or not reason.strip():
        raise BizError(error_code="INVALID_ARGUMENT", message="作废原因不能为空")
    if len(reason.strip()) < 5:
        raise BizError(error_code="INVALID_ARGUMENT", message="作废原因至少需要5个字符")
    if len(reason.strip()) > 200:
        raise BizError(error_code="INVALID_ARGUMENT", message="作废原因不能超过200个字符")

    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")

        # 禁止作废的状态
        forbidden_void = ("CREATED", "IMPORTING", "CHECKING", "CALCULATING", "VOIDED", "LOCKED", "EXPORTED")
        if run.status in forbidden_void:
            status_label = run.status
            if run.status in ("IMPORTING", "CHECKING", "CALCULATING"):
                raise BizError(
                    error_code="RUN_STATUS_NOT_ALLOWED",
                    message=f"任务正在「{status_label}」中，请等待操作完成后再试",
                )
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"任务当前状态为「{status_label}」，不允许作废",
            )

        now = datetime.now()
        old_status = run.status
        run.status = "VOIDED"
        run.void_reason = reason.strip()
        run.voided_by = voided_by
        run.voided_at = now
        db.commit()

        # 记录审计日志
        _log_audit(db, run_id, "PAYROLL_TASK_VOID", {
            "task_name": run.name,
            "payroll_month": run.payroll_month,
            "old_status": old_status,
            "new_status": "VOIDED",
            "reason": reason.strip(),
            "operator": voided_by,
        }, voided_by)

        return _run_to_dict(run)
    finally:
        db.close()


def archive_run(run_id: str, archived_by: str) -> dict:
    """归档任务"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id, SalaryRun.delete_flag == 0).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {run_id}")

        allowed_archive = ("EXPORTED", "LOCKED", "VOIDED", "FAILED")
        if run.status not in allowed_archive:
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"任务当前状态为「{run.status}」，不允许归档",
            )

        now = datetime.now()
        run.archive_flag = 1
        run.archived_by = archived_by
        run.archived_at = now
        db.commit()

        _log_audit(db, run_id, "PAYROLL_TASK_ARCHIVE", {
            "task_name": run.name,
            "payroll_month": run.payroll_month,
            "status": run.status,
            "operator": archived_by,
        }, archived_by)

        return _run_to_dict(run)
    finally:
        db.close()


def _log_audit(db: SessionLocal, salary_run_id: str, event: str, detail: dict, operator: str):
    """记录审计日志"""
    from app.models import AuditLog
    import uuid as _uuid
    log = AuditLog(
        id=f"log_{_uuid.uuid4().hex[:8]}",
        salary_run_id=salary_run_id,
        event=event,
        detail=json.dumps(detail, ensure_ascii=False),
        operator=operator,
        request_id="",
    )
    db.add(log)
    db.commit()


def _run_to_dict(run: SalaryRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "payroll_month": run.payroll_month,
        "status": run.status,
        "remark": run.remark or None,
        "block_count": 0,
        "warn_count": 0,
        "current_calc_version": run.current_calc_version,
        "created_by": run.created_by,
        "created_at": run.created_at.isoformat() if run.created_at else "",
        "updated_at": run.updated_at.isoformat() if run.updated_at else "",
        "delete_flag": run.delete_flag,
        "archive_flag": run.archive_flag,
        "void_reason": run.void_reason,
        "voided_by": run.voided_by,
        "voided_at": run.voided_at.isoformat() if run.voided_at else None,
        "deleted_by": run.deleted_by,
        "deleted_at": run.deleted_at.isoformat() if run.deleted_at else None,
        "archived_by": run.archived_by,
        "archived_at": run.archived_at.isoformat() if run.archived_at else None,
        "reference_run_id": run.reference_run_id or None,
        "run_version": run.run_version or "DRAFT",
    }
