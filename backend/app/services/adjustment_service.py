"""人工调整项服务"""

import uuid
from decimal import Decimal

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import AdjustmentItem, EmployeeRecord, SalaryRun


def _gen_id() -> str:
    return f"adj_{uuid.uuid4().hex[:8]}"


def list_adjustments(salary_run_id: str, employee_record_id: str | None = None) -> list[dict]:
    """查询所有调整项"""
    db = SessionLocal()
    try:
        query = db.query(AdjustmentItem).filter(
            AdjustmentItem.salary_run_id == salary_run_id,
        )
        if employee_record_id:
            query = query.filter(AdjustmentItem.employee_record_id == employee_record_id)
        query = query.order_by(AdjustmentItem.created_at.desc())
        items = []
        for adj in query.all():
            emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == adj.employee_record_id).first()
            items.append(_adj_to_dict(adj, emp.employee_name if emp else "未知"))
        return items
    finally:
        db.close()


def create_adjustment(
    salary_run_id: str,
    employee_record_id: str,
    field_code: str,
    adjustment_type: str,
    amount: str,
    reason: str,
    created_by: str,
) -> dict:
    """创建调整项"""
    db = SessionLocal()
    try:
        # 验证任务存在
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        # 验证员工存在
        emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == employee_record_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")

        amount_val = Decimal(str(amount)).quantize(Decimal("0.01"))

        adj = AdjustmentItem(
            id=_gen_id(),
            salary_run_id=salary_run_id,
            employee_record_id=employee_record_id,
            field_code=field_code,
            adjustment_type=adjustment_type,
            amount=amount_val,
            reason=reason,
            created_by=created_by,
            status="ACTIVE",
        )
        db.add(adj)
        db.commit()
        db.refresh(adj)

        return _adj_to_dict(adj, emp.employee_name)
    except BizError:
        raise
    finally:
        db.close()


def revert_adjustment(adjustment_id: str, reverted_by: str) -> dict:
    """撤销调整项"""
    db = SessionLocal()
    try:
        adj = db.query(AdjustmentItem).filter(AdjustmentItem.id == adjustment_id).first()
        if not adj:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="调整项不存在")
        if adj.status != "ACTIVE":
            raise BizError(error_code="INVALID_ARGUMENT", message="调整项已被撤销")

        from datetime import datetime
        adj.status = "REVERTED"
        adj.reverted_by = reverted_by
        adj.reverted_at = datetime.now()
        db.commit()

        emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == adj.employee_record_id).first()
        return _adj_to_dict(adj, emp.employee_name if emp else "未知")
    finally:
        db.close()


def _adj_to_dict(adj: AdjustmentItem, employee_name: str) -> dict:
    return {
        "id": adj.id,
        "salary_run_id": adj.salary_run_id,
        "employee_record_id": adj.employee_record_id,
        "employee_name": employee_name,
        "field_code": adj.field_code,
        "adjustment_type": adj.adjustment_type,
        "amount": str(adj.amount),
        "reason": adj.reason,
        "created_by": adj.created_by,
        "created_at": adj.created_at.isoformat() if adj.created_at else "",
        "status": adj.status,
        "reverted_at": adj.reverted_at.isoformat() if adj.reverted_at else None,
        "reverted_by": adj.reverted_by,
    }
