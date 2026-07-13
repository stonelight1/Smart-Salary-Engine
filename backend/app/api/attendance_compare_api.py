"""
员工异动待确认 API
"""

import logging

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.attendance_compare_service import (
    import_attendance_employees, list_change_candidates,
    handle_change_candidate, batch_confirm, get_candidate_counts,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/attendance-compare", tags=["attendance-compare"])


@router.post("/import")
def api_import_attendance(
    file: UploadFile = File(...),
    salary_month: str = Form(...),
    user: dict = Depends(get_current_user),
):
    try:
        content = file.file.read()
        result = import_attendance_employees(
            file_bytes=content,
            original_name=file.filename or "attendance.xlsx",
            salary_month=salary_month,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("考导入异常: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="EXCEL_PARSE_FAILED", message="考导入失败。")


@router.get("/candidates")
def api_list_candidates(
    status: str = Query("PENDING"),
    candidate_type: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50),
    user: dict = Depends(get_current_user),
):
    try:
        result = list_change_candidates(status=status, candidate_type=candidate_type, page=page, page_size=page_size)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/counts")
def api_get_counts(user: dict = Depends(get_current_user)):
    try:
        result = get_candidate_counts()
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/handle/{candidate_id}")
def api_handle_candidate(
    candidate_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        result = handle_change_candidate(
            candidate_id,
            action=body.get("action", ""),
            handle_data=body.get("data", {}),
            handled_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/batch-confirm")
def api_batch_confirm(
    body: dict,
    user: dict = Depends(get_current_user),
):
    try:
        result = batch_confirm(
            action=body.get("action", "CONFIRM_HIRE"),
            candidate_ids=body.get("candidate_ids", []),
            handle_data=body.get("data", {}),
            handled_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
