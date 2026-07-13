"""
月度快照 API
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.snapshot_service import (
    generate_monthly_snapshots, calculate_snapshot_salary,
    add_salary_item, list_snapshots,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/snapshots", tags=["snapshots-v4"])


@router.post("/generate/{run_id}")
def api_generate_snapshots(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    try:
        result = generate_monthly_snapshots(run_id, created_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/{run_id}")
def api_list_snapshots(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    try:
        result = list_snapshots(run_id, page=page, page_size=page_size)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{snapshot_id}/calculate")
def api_calculate_snapshot(
    snapshot_id: str,
    user: dict = Depends(get_current_user),
):
    try:
        result = calculate_snapshot_salary(snapshot_id)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{snapshot_id}/items")
def api_add_salary_item(
    snapshot_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        if not body.get("item_type") or not body.get("item_code"):
            raise BizError(error_code="INVALID_ARGUMENT", message="项目类型和编码不能为空")
        result = add_salary_item(
            snapshot_id,
            item_type=body["item_type"],
            item_code=body["item_code"],
            item_name=body.get("item_name", ""),
            amount=Decimal(str(body.get("amount", 0))),
            source=body.get("source", "MANUAL"),
            remark=body.get("remark", ""),
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
