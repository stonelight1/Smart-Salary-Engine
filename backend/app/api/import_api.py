"""文件导入、Sheet/列映射接口"""

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.import_service import import_file
from app.db.database import SessionLocal
from app.models import SheetMapping, ColumnMapping, ImportBatch, WorkbookFile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["import"])


# ----- 上传 -----

@router.post("/salary-runs/{run_id}/files")
def api_upload_file(
    run_id: str,
    file: UploadFile = File(...),
    file_role: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """上传 Excel 文件（主表或补充表）"""
    try:
        content = file.file.read()
        result = import_file(
            file_bytes=content,
            original_name=file.filename or "unknown.xlsx",
            salary_run_id=run_id,
            file_role=file_role,
            created_by=user["username"],
        )

        # 构建响应
        response = {"success": True, "data": result, "request_id": ""}

        # 如果有修复信息，添加到响应顶层
        if result.get("repaired"):
            if result.get("repair_method") == "VALUE_ONLY_REBUILD":
                response["message"] = "文件已通过兼容模式读取，系统未修改原始 Excel。"
                response["warnings"] = result.get("warnings", [])
            else:
                response["message"] = "文件已自动修复并成功读取，系统未修改原始 Excel。"
        else:
            response["message"] = "文件读取成功"

        return response

    except BizError:
        raise
    except Exception as e:
        logger.error("文件上传异常: %s", str(e)[:300], exc_info=True)
        raise BizError(
            error_code="EXCEL_PARSE_FAILED",
            message="文件上传失败，请稍后重试。",
        )


# ----- 文件列表 -----

@router.get("/salary-runs/{run_id}/files")
def api_list_files(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """查询任务的所有导入文件"""
    db = SessionLocal()
    try:
        batches = (
            db.query(ImportBatch, WorkbookFile)
            .join(WorkbookFile, ImportBatch.file_id == WorkbookFile.id)
            .filter(ImportBatch.salary_run_id == run_id)
            .order_by(ImportBatch.created_at.desc())
            .all()
        )
        items = []
        for ib, wf in batches:
            # 统计该批次的异常数
            sheet_count = db.query(SheetMapping).filter(SheetMapping.import_batch_id == ib.id).count()
            items.append({
                "batch_id": ib.id,
                "file_id": wf.id,
                "file_name": wf.original_name,
                "file_size": wf.file_size,
                "file_role": ib.file_role,
                "status": ib.status,
                "sheet_count": sheet_count,
                "created_by": ib.created_by,
                "created_at": ib.created_at.isoformat() if ib.created_at else "",
            })
        return {"success": True, "data": {"items": items}, "request_id": ""}
    finally:
        db.close()


# ----- Sheet 查询/确认 -----

@router.get("/import-batches/{batch_id}/sheets")
def api_get_sheets(
    batch_id: str,
    user: dict = Depends(get_current_user),
):
    """查询导入批次的 Sheet 识别结果"""
    db = SessionLocal()
    try:
        sheets = db.query(SheetMapping).filter(SheetMapping.import_batch_id == batch_id).all()
        items = [
            {
                "sheet_mapping_id": s.id,
                "sheet_name": s.sheet_name,
                "sheet_type": s.sheet_type,
                "confidence": s.confidence,
                "need_confirm": s.need_confirm,
                "row_count": 0,
                "header_row_index": s.header_row_index,
            }
            for s in sheets
        ]
        return {"success": True, "data": {"items": items}, "request_id": ""}
    finally:
        db.close()


@router.patch("/sheet-mappings/{sheet_mapping_id}")
def api_update_sheet(
    sheet_mapping_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """确认/修改 Sheet 类型"""
    db = SessionLocal()
    try:
        sm = db.query(SheetMapping).filter(SheetMapping.id == sheet_mapping_id).first()
        if not sm:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="Sheet 映射不存在")
        if "sheet_type" in body:
            sm.sheet_type = body["sheet_type"]
        if "header_row_index" in body:
            sm.header_row_index = body["header_row_index"]
        sm.confirmed_by = user["username"]
        db.commit()
        return {"success": True, "data": {"sheet_mapping_id": sm.id, "status": "confirmed"}, "request_id": ""}
    except BizError:
        raise
    finally:
        db.close()


# ----- 列映射查询/确认 -----

@router.get("/sheet-mappings/{sheet_mapping_id}/columns")
def api_get_columns(
    sheet_mapping_id: str,
    user: dict = Depends(get_current_user),
):
    """查询 Sheet 的列映射结果"""
    db = SessionLocal()
    try:
        cols = db.query(ColumnMapping).filter(ColumnMapping.sheet_mapping_id == sheet_mapping_id).all()
        items = [
            {
                "column_mapping_id": c.id,
                "original_column": c.original_column,
                "field_code": c.field_code,
                "field_name": c.field_name,
                "confidence": c.confidence,
                "need_confirm": c.need_confirm,
            }
            for c in cols
        ]
        return {"success": True, "data": {"items": items}, "request_id": ""}
    finally:
        db.close()


@router.patch("/column-mappings/{column_mapping_id}")
def api_update_column(
    column_mapping_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """确认/修改列映射"""
    db = SessionLocal()
    try:
        cm = db.query(ColumnMapping).filter(ColumnMapping.id == column_mapping_id).first()
        if not cm:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="列映射不存在")
        if "field_code" in body:
            cm.field_code = body["field_code"]
        db.commit()
        return {"success": True, "data": {"column_mapping_id": cm.id, "status": "confirmed"}, "request_id": ""}
    except BizError:
        raise
    finally:
        db.close()
