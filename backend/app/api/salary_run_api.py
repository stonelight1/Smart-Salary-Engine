"""Salary Run 接口"""

from fastapi import APIRouter, Depends

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.services.run_service import (
    create_run, list_runs, get_run, confirm_run, lock_run, unlock_run,
    delete_run, void_run, archive_run,
)

router = APIRouter(prefix="/api/v1/salary-runs", tags=["salary-runs"])


@router.post("")
def api_create_run(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """创建工资核算任务"""
    try:
        result = create_run(
            name=body.get("name", ""),
            payroll_month=body.get("payroll_month", ""),
            remark=body.get("remark"),
            created_by=user["username"],
            reference_run_id=body.get("reference_run_id"),
            run_version=body.get("run_version", "DRAFT"),
            reference_source_type=body.get("reference_source_type", "SYSTEM_FINAL"),
            reference_external_id=body.get("reference_external_id"),
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("")
def api_list_runs(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    include_archived: bool = False,
    user: dict = Depends(get_current_user),
):
    """查询任务列表"""
    try:
        result = list_runs(page=page, page_size=page_size, keyword=keyword, include_archived=include_archived)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/{run_id}")
def api_get_run(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """查询任务详情"""
    try:
        result = get_run(run_id)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/confirm")
def api_confirm_run(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """确认任务"""
    try:
        result = confirm_run(run_id, confirmed_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/lock")
def api_lock_run(
    run_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """锁定任务"""
    try:
        result = lock_run(run_id, reason=body.get("reason", ""), locked_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/unlock")
def api_unlock_run(
    run_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """解锁任务"""
    try:
        result = unlock_run(run_id, reason=body.get("reason", ""), unlocked_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/delete")
def api_delete_run(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """删除任务（仅空任务可删除）"""
    try:
        result = delete_run(run_id, deleted_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/void")
def api_void_run(
    run_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """作废任务"""
    try:
        result = void_run(run_id, reason=body.get("reason", ""), voided_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.post("/{run_id}/archive")
def api_archive_run(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """归档任务"""
    try:
        result = archive_run(run_id, archived_by=user["username"])
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
