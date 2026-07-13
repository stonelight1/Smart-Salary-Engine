"""
员工档案管理 API
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.employee_service import (
    list_employees, get_employee, create_employee,
    update_employee, resign_employee,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/employees", tags=["employees-v4"])


@router.get("")
def api_list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    include_resigned: bool = Query(False),
    status: str = Query(""),
    user: dict = Depends(get_current_user),
):
    try:
        result = list_employees(page=page, page_size=page_size, keyword=keyword, include_resigned=include_resigned, status=status)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/{employee_id}")
def api_get_employee(
    employee_id: str,
    user: dict = Depends(get_current_user),
):
    try:
        result = get_employee(employee_id)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("")
def api_create_employee(
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        if not body.get("employee_name"):
            raise BizError(error_code="INVALID_ARGUMENT", message="员工姓名不能为空")
        result = create_employee(body, created_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.put("/{employee_id}")
def api_update_employee(
    employee_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        result = update_employee(employee_id, body, created_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{employee_id}/resign")
def api_resign_employee(
    employee_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        result = resign_employee(
            employee_id,
            resign_date=body.get("resign_date", ""),
            reason=body.get("reason", ""),
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/stats/overview")
def api_employee_overview(user: dict = Depends(get_current_user)):
    """员工统计数据（用于前端卡片）"""
    from app.db.database import SessionLocal
    from app.models import EmployeeMaster, EmployeeChangeCandidate
    db = SessionLocal()
    try:
        # 基础查询：排除无效名称
        valid_employees = db.query(EmployeeMaster).filter(
            EmployeeMaster.employee_name.isnot(None),
            EmployeeMaster.employee_name != "",
            EmployeeMaster.employee_name != "None",
            EmployeeMaster.employee_name != "null",
            EmployeeMaster.employee_name != "undefined",
        )

        active_count = valid_employees.filter(EmployeeMaster.status == "ACTIVE").count()
        resigned_count = valid_employees.filter(EmployeeMaster.status.in_(["RESIGNED", "TERMINATED"])).count()
        total = active_count + resigned_count

        # 待确认异动统计
        pending_candidates = db.query(EmployeeChangeCandidate).filter(
            EmployeeChangeCandidate.status == "PENDING",
        ).count()
        pending_hire = db.query(EmployeeChangeCandidate).filter(
            EmployeeChangeCandidate.status == "PENDING",
            EmployeeChangeCandidate.candidate_type == "POSSIBLE_HIRE",
        ).count()
        pending_term = db.query(EmployeeChangeCandidate).filter(
            EmployeeChangeCandidate.status == "PENDING",
            EmployeeChangeCandidate.candidate_type == "POSSIBLE_TERMINATION",
        ).count()
        pending_dept = db.query(EmployeeChangeCandidate).filter(
            EmployeeChangeCandidate.status == "PENDING",
            EmployeeChangeCandidate.candidate_type.in_(["DEPARTMENT_CHANGE", "POSITION_CHANGE"]),
        ).count()
        pending_conflict = db.query(EmployeeChangeCandidate).filter(
            EmployeeChangeCandidate.status == "PENDING",
            EmployeeChangeCandidate.candidate_type == "INFO_CONFLICT",
        ).count()

        return {
            "success": True,
            "data": {
                "total": total,
                "active": active_count,
                "resigned": resigned_count,
                "pending_candidates": pending_candidates,
                "pending_hire": pending_hire,
                "pending_termination": pending_term,
                "pending_department_change": pending_dept,
                "pending_conflict": pending_conflict,
            },
            "request_id": "",
        }
    finally:
        db.close()
