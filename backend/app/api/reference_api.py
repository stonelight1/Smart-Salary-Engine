"""
引用版本 API

端点：
- POST /api/v2/reference/parse — 解析上传的 Excel
- POST /api/v2/reference/save — 保存引用版本
- POST /api/v2/reference/{id}/confirm-draft — 确认引用并创建草稿
- POST /api/v2/reference/check-hash — 检查文件是否已上传
"""

import json
import logging

from fastapi import APIRouter, Depends, File, UploadFile, Form, Body

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.db.database import SessionLocal
from app.models import SalaryReferenceSource, SalaryRun

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/reference", tags=["reference"])


@router.post("/parse")
def api_parse_reference(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """解析上传的上月最终工资表 Excel"""
    from app.services.reference_service import parse_reference_excel

    try:
        content = file.file.read()
        result = parse_reference_excel(
            file_bytes=content,
            original_name=file.filename or "reference.xlsx",
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("解析引用Excel异常: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="EXCEL_PARSE_FAILED", message="Excel 解析失败，请确认文件格式正确。")


@router.post("/save")
def api_save_reference(
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """保存外部引用版本"""
    from app.services.reference_service import create_reference_source

    try:
        file_bytes_hex = body.get("file_bytes_hex")
        original_name = body.get("original_name", "reference.xlsx")
        parsed = body.get("parsed", {})
        target_salary_month = body.get("target_salary_month", "")
        reference_salary_month = body.get("reference_salary_month", "")

        if not file_bytes_hex:
            raise BizError(error_code="INVALID_ARGUMENT", message="缺少文件数据")

        file_bytes = bytes.fromhex(file_bytes_hex) if isinstance(file_bytes_hex, str) else b""

        result = create_reference_source(
            file_bytes=file_bytes,
            original_name=original_name,
            parsed=parsed,
            target_salary_month=target_salary_month,
            reference_salary_month=reference_salary_month,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("保存引用版本异常: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="保存引用版本失败。")


@router.post("/save-from-upload")
def api_save_reference_from_upload(
    file: UploadFile = File(...),
    original_name: str = Form(...),
    target_salary_month: str = Form(...),
    reference_salary_month: str = Form(...),
    parsed_json: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """保存引用版本（从上传直接保存，避免前端传 hex）"""
    from app.services.reference_service import parse_reference_excel, create_reference_source

    try:
        content = file.file.read()
        parsed = json.loads(parsed_json)

        result = create_reference_source(
            file_bytes=content,
            original_name=original_name,
            parsed=parsed,
            target_salary_month=target_salary_month,
            reference_salary_month=reference_salary_month,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("保存引用版本异常: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="保存引用版本失败。")


@router.post("/{reference_id}/confirm-draft")
def api_confirm_reference_and_create_draft(
    reference_id: str,
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """确认引用版本并创建本月工资草稿"""
    from app.services.reference_service import confirm_reference_and_create_draft

    target_run_id = body.get("target_run_id")
    if not target_run_id:
        raise BizError(error_code="INVALID_ARGUMENT", message="缺少目标任务 ID")

    try:
        result = confirm_reference_and_create_draft(
            reference_id=reference_id,
            target_run_id=target_run_id,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("确认引用并创建草稿异常: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="确认引用并创建草稿失败。")


@router.post("/check-hash")
def api_check_hash(
    body: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """检查文件哈希是否已存在"""
    file_hash = body.get("file_hash", "")
    target_month = body.get("target_month", "")

    if not file_hash:
        raise BizError(error_code="INVALID_ARGUMENT", message="缺少文件哈希")

    db = SessionLocal()
    try:
        existing = db.query(SalaryReferenceSource).filter(
            SalaryReferenceSource.file_hash == file_hash,
            SalaryReferenceSource.target_salary_month == target_month,
        ).first()

        return {
            "success": True,
            "data": {
                "exists": existing is not None,
                "reference_id": existing.id if existing else None,
                "status": existing.status if existing else None,
            },
            "request_id": "",
        }
    finally:
        db.close()
