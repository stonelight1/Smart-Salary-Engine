"""数据检查与异常处理接口"""

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.check_service import execute_check, list_issues, resolve_issue
from app.db.database import SessionLocal
from app.models import CheckIssue, EmployeeRecord

router = APIRouter(prefix="/api/v1", tags=["check"])


@router.post("/salary-runs/{run_id}/check")
def api_run_check(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """发起数据检查"""
    try:
        result = execute_check(run_id)
        return {
            "success": True,
            "data": {
                "status": "CHECK_FAILED" if result["block_count"] > 0 else "CHECK_PASSED",
                "block_count": result["block_count"],
                "warn_count": result["warn_count"],
                "info_count": result["info_count"],
            },
            "request_id": "",
        }
    except BizError:
        raise


@router.get("/salary-runs/{run_id}/issues")
def api_get_issues(
    run_id: str,
    level: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """查询异常列表"""
    try:
        result = list_issues(run_id, level=level, status=status, page=page, page_size=page_size)
        # 获取员工姓名
        db = SessionLocal()
        try:
            for item in result["items"]:
                if item.get("issue_id"):
                    issue = db.query(CheckIssue).filter(
                        CheckIssue.id == item["issue_id"]
                    ).first()
                    if issue and issue.employee_record_id:
                        emp = db.query(EmployeeRecord).filter(
                            EmployeeRecord.id == issue.employee_record_id
                        ).first()
                        if emp:
                            item["employee_name"] = emp.employee_name
        finally:
            db.close()

        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.patch("/issues/{issue_id}")
def api_resolve_issue(
    issue_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """处理异常"""
    try:
        result = resolve_issue(
            issue_id=issue_id,
            action=body.get("action", ""),
            value=body.get("value"),
            reason=body.get("reason"),
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
