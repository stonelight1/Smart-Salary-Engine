"""人工调整项接口"""

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.adjustment_service import (
    list_adjustments,
    create_adjustment,
    revert_adjustment,
)

router = APIRouter(prefix="/api/v1", tags=["adjustment"])


@router.get("/salary-runs/{run_id}/adjustments")
def api_list_adjustments(
    run_id: str,
    employee_id: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """查询调整项列表"""
    try:
        items = list_adjustments(run_id, employee_record_id=employee_id)
        return {"success": True, "data": {"items": items}, "request_id": ""}
    except BizError:
        raise


@router.post("/salary-runs/{run_id}/adjustments")
def api_create_adjustment(
    run_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """创建调整项"""
    try:
        result = create_adjustment(
            salary_run_id=run_id,
            employee_record_id=body.get("employee_record_id", ""),
            field_code=body.get("field_code", ""),
            adjustment_type=body.get("adjustment_type", ""),
            amount=body.get("amount", "0"),
            reason=body.get("reason", ""),
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/adjustments/{adjustment_id}/revert")
def api_revert_adjustment(
    adjustment_id: str,
    user: dict = Depends(get_current_user),
):
    """撤销调整项"""
    try:
        result = revert_adjustment(adjustment_id, reverted_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
