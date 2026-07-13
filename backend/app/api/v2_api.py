"""
工资核算 V2 接口

新增：
- 绩效得分导入
- 请假记录导入
- 草稿生成
- 版本确认
"""

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, Body

from app.core.exceptions import BizError
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/runs", tags=["salary-v2"])


# ============================================================
#  绩效得分导入
# ============================================================

@router.post("/{run_id}/performance/import")
def api_import_performance(
    run_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """导入绩效得分 Excel"""
    from app.services.performance_service import import_performance_scores

    try:
        content = file.file.read()
        result = import_performance_scores(
            file_bytes=content,
            original_name=file.filename or "performance.xlsx",
            salary_run_id=run_id,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("绩效导入异常: %s", str(e)[:200], exc_info=True)
        raise BizError(
            error_code="EXCEL_PARSE_FAILED",
            message="绩效导入失败，请检查文件格式。",
        )


@router.get("/{run_id}/performance/status")
def api_get_performance_status(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """查询绩效导入状态"""
    from app.db.database import SessionLocal
    from app.models import EmployeeRecord, PerformanceImportRecord

    db = SessionLocal()
    try:
        imported = db.query(PerformanceImportRecord).filter(
            PerformanceImportRecord.salary_run_id == run_id,
            PerformanceImportRecord.status == "MATCHED",
        ).count()

        unmatched = db.query(PerformanceImportRecord).filter(
            PerformanceImportRecord.salary_run_id == run_id,
            PerformanceImportRecord.status == "UNMATCHED",
        ).count()

        total_emps = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == run_id,
            EmployeeRecord.status.in_(["NORMAL"]),
        ).count()

        default_score_emps = total_emps - imported

        return {
            "success": True,
            "data": {
                "total_employees": total_emps,
                "imported_count": imported,
                "default_score_count": max(default_score_emps, 0),
                "unmatched_count": unmatched,
            },
            "request_id": "",
        }
    finally:
        db.close()


# ============================================================
#  请假导入
# ============================================================

@router.post("/{run_id}/leave/import")
def api_import_leave(
    run_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """导入企业微信请假 Excel"""
    from app.services.leave_service import import_leave_records

    try:
        content = file.file.read()
        result = import_leave_records(
            file_bytes=content,
            original_name=file.filename or "leave.xlsx",
            salary_run_id=run_id,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("请假导入异常: %s", str(e)[:200], exc_info=True)
        raise BizError(
            error_code="EXCEL_PARSE_FAILED",
            message="请假导入失败，请检查文件格式。",
        )


@router.get("/{run_id}/leave/status")
def api_get_leave_status(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """查询请假导入状态"""
    from app.db.database import SessionLocal
    from app.models import EmployeeRecord, LeaveImportRecord
    from sqlalchemy import func

    db = SessionLocal()
    try:
        matched = db.query(LeaveImportRecord).filter(
            LeaveImportRecord.salary_run_id == run_id,
            LeaveImportRecord.status == "MATCHED",
        ).count()

        unmatched = db.query(LeaveImportRecord).filter(
            LeaveImportRecord.salary_run_id == run_id,
            LeaveImportRecord.status == "UNMATCHED",
        ).count()

        duplicate = db.query(LeaveImportRecord).filter(
            LeaveImportRecord.salary_run_id == run_id,
            LeaveImportRecord.status == "DUPLICATE",
        ).count()

        total_days = db.query(func.sum(LeaveImportRecord.leave_days)).filter(
            LeaveImportRecord.salary_run_id == run_id,
            LeaveImportRecord.status == "MATCHED",
        ).scalar() or 0

        emp_with_leave = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == run_id,
            EmployeeRecord.leave_days > 0,
        ).count()

        return {
            "success": True,
            "data": {
                "matched_record_count": matched,
                "employee_with_leave_count": emp_with_leave,
                "total_leave_days": str(total_days),
                "unmatched_count": unmatched,
                "duplicate_count": duplicate,
            },
            "request_id": "",
        }
    finally:
        db.close()


# ============================================================
#  草稿生成
# ============================================================

@router.post("/{run_id}/generate-draft")
def api_generate_draft(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """从引用版本生成本月工资草稿"""
    from app.services.draft_service import generate_draft_from_reference

    try:
        result = generate_draft_from_reference(
            target_run_id=run_id,
            created_by=user["username"],
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
    except Exception as e:
        logger.error("草稿生成异常: %s", str(e)[:200], exc_info=True)
        raise BizError(
            error_code="INTERNAL_ERROR",
            message="工资草稿生成失败。",
        )


# ============================================================
#  版本确认（标记为最终版）
# ============================================================

@router.post("/{run_id}/confirm-final")
def api_confirm_final(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """确认本月最终版"""
    from app.db.database import SessionLocal
    from app.models import SalaryRun, CheckIssue

    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        if run.status != "CONFIRMED":
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"当前状态为「{run.status}」，需要先确认（CONFIRMED）才能设为最终版",
            )

        # 检查是否有未解决的 BLOCK 异常
        open_blocks = db.query(CheckIssue).filter(
            CheckIssue.salary_run_id == run_id,
            CheckIssue.level == "BLOCK",
            CheckIssue.status == "OPEN",
        ).count()
        if open_blocks > 0:
            raise BizError(
                error_code="BLOCK_ISSUE_EXISTS",
                message=f"存在 {open_blocks} 个未处理的严重异常，请先处理后再确认最终版",
            )

        run.run_version = "FINAL"
        run.status = "LOCKED"
        db.commit()

        logger.info("任务已标记为最终版: run=%s, month=%s", run_id, run.payroll_month)

        return {
            "success": True,
            "data": {
                "run_id": run_id,
                "run_version": "FINAL",
                "status": "LOCKED",
            },
            "request_id": "",
        }
    except BizError:
        raise
    finally:
        db.close()
