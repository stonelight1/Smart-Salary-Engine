"""导出接口"""

from fastapi import APIRouter, Depends
from starlette.responses import FileResponse

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.engines.exporter.exporter import export_salary
from app.db.database import SessionLocal
from app.models import ExportFile

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.post("/salary-runs/{run_id}/export")
def api_export(
    run_id: str,
    body: dict = {},
    user: dict = Depends(get_current_user),
):
    """导出工资结果"""
    try:
        result = export_salary(
            salary_run_id=run_id,
            calc_version=body.get("calc_version", 0),
            include_trace=body.get("include_trace", True),
            include_issues=body.get("include_issues", True),
            include_sources=body.get("include_sources", True),
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/export-files/{export_file_id}/download")
def api_download(
    export_file_id: str,
    user: dict = Depends(get_current_user),
):
    """下载导出文件"""
    db = SessionLocal()
    try:
        ef = db.query(ExportFile).filter(ExportFile.id == export_file_id).first()
        if not ef:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="导出文件不存在")

        file_path = ef.storage_path
        return FileResponse(
            path=file_path,
            filename=ef.file_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except BizError:
        raise
    finally:
        db.close()
