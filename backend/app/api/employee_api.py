"""员工数据池接口"""

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.db.database import SessionLocal
from app.models import EmployeeRecord, EmployeeFieldValue

router = APIRouter(prefix="/api/v1", tags=["employees"])


@router.get("/salary-runs/{run_id}/employees")
def api_list_employees(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    user: dict = Depends(get_current_user),
):
    """查询员工数据池列表"""
    db = SessionLocal()
    try:
        query = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == run_id,
            EmployeeRecord.status != "IGNORED",
        )
        if keyword:
            query = query.filter(EmployeeRecord.employee_name.contains(keyword))

        total = query.count()
        employees = query.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for emp in employees:
            fields_values = db.query(EmployeeFieldValue).filter(
                EmployeeFieldValue.employee_record_id == emp.id
            ).all()

            fields: dict[str, str] = {}
            issue_count = 0
            for fv in fields_values:
                val = str(fv.value_decimal) if fv.value_decimal is not None else fv.value_text or ""
                if val:
                    fields[fv.field_code] = val

            from app.models import CheckIssue
            issue_count = db.query(CheckIssue).filter(
                CheckIssue.employee_record_id == emp.id,
                CheckIssue.status == "OPEN",
            ).count()

            items.append({
                "employee_ref_id": emp.id,
                "employee_name": emp.employee_name,
                "status": emp.status,
                "fields": fields,
                "issue_count": issue_count,
            })

        return {"success": True, "data": {"items": items, "total": total}, "request_id": ""}
    finally:
        db.close()


@router.get("/employees/{employee_ref_id}")
def api_get_employee(
    employee_ref_id: str,
    user: dict = Depends(get_current_user),
):
    """查询员工详情（含字段来源）"""
    db = SessionLocal()
    try:
        emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == employee_ref_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")

        fields_values = db.query(EmployeeFieldValue).filter(
            EmployeeFieldValue.employee_record_id == emp.id
        ).all()

        from app.models import CheckIssue
        issues = db.query(CheckIssue).filter(
            CheckIssue.employee_record_id == emp.id,
        ).all()

        fields_detail = {}
        for fv in fields_values:
            fields_detail[fv.field_code] = {
                "value": str(fv.value_decimal) if fv.value_decimal is not None else fv.value_text or "",
                "value_type": fv.value_type,
                "is_manual": fv.is_manual,
                "source": {
                    "source_file_id": fv.source_file_id,
                    "source_sheet": fv.source_sheet,
                    "source_row": fv.source_row,
                    "source_column": fv.source_column,
                },
            }

        return {
            "success": True,
            "data": {
                "employee_ref_id": emp.id,
                "employee_name": emp.employee_name,
                "status": emp.status,
                "fields": fields_detail,
                "issues": [
                    {
                        "issue_id": iss.id,
                        "level": iss.level,
                        "issue_code": iss.issue_code,
                        "message": iss.message,
                        "status": iss.status,
                    }
                    for iss in issues
                ],
            },
            "request_id": "",
        }
    except BizError:
        raise
    finally:
        db.close()


@router.patch("/employees/{employee_ref_id}/fields/{field_code}")
def api_update_employee_field(
    employee_ref_id: str,
    field_code: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """人工修改员工字段值"""
    from datetime import datetime

    db = SessionLocal()
    try:
        emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == employee_ref_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")

        value = body.get("value", "")
        reason = body.get("reason", "")

        if not reason:
            raise BizError(error_code="INVALID_ARGUMENT", message="人工修改必须填写原因")

        import uuid
        from decimal import Decimal

        fv = EmployeeFieldValue(
            id=f"fv_{uuid.uuid4().hex[:8]}",
            employee_record_id=employee_ref_id,
            field_code=field_code,
            value_text=value,
            value_decimal=Decimal(value) if value else None,
            value_type="money",
            source_file_id="manual",
            source_sheet="manual",
            source_row=0,
            source_column=field_code,
            import_batch_id="manual",
            is_manual=True,
            manual_reason=reason,
            manual_by=user["username"],
            manual_at=datetime.now(),
        )
        db.add(fv)
        db.commit()

        return {"success": True, "data": {"status": "updated"}, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        raise BizError(error_code="INVALID_ARGUMENT", message=f"字段更新失败: {str(e)}")
    finally:
        db.close()
