"""检查与异常处理服务"""

import uuid

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.engines.checker.checker import run_checks
from app.models import CheckIssue, SalaryRun


def execute_check(salary_run_id: str) -> dict:
    """执行检查并返回结果"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")
        if run.status == "CREATED":
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message="尚未导入 Excel，无法执行检查",
            )

        result = run_checks(salary_run_id)
        return result
    except BizError:
        raise
    finally:
        db.close()


def list_issues(
    salary_run_id: str,
    level: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """查询异常列表"""
    db = SessionLocal()
    try:
        query = db.query(CheckIssue).filter(
            CheckIssue.salary_run_id == salary_run_id,
        )

        if level:
            query = query.filter(CheckIssue.level == level.upper())
        if status:
            query = query.filter(CheckIssue.status == status.upper())

        query = query.order_by(
            CheckIssue.level.desc(),
            CheckIssue.created_at.asc(),
        )

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [_issue_to_dict(i) for i in items],
            "total": total,
        }
    finally:
        db.close()


def resolve_issue(issue_id: str, action: str, value: str | None = None, reason: str | None = None) -> dict:
    """处理异常"""
    from datetime import datetime

    db = SessionLocal()
    try:
        issue = db.query(CheckIssue).filter(CheckIssue.id == issue_id).first()
        if not issue:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="异常不存在")

        if issue.status != "OPEN":
            raise BizError(
                error_code="INVALID_ARGUMENT",
                message=f"异常已处理: {issue.status}",
            )

        if action == "IGNORE_ISSUE":
            if issue.level == "BLOCK":
                raise BizError(
                    error_code="INVALID_ARGUMENT",
                    message="BLOCK 异常不能直接忽略",
                )
            issue.status = "IGNORED"
        elif action == "CONFIRM":
            issue.status = "RESOLVED"
        elif action == "FILL_VALUE":
            issue.status = "RESOLVED"
        elif action == "IGNORE_ROW":
            issue.status = "RESOLVED"
            if issue.employee_record_id:
                from app.models import EmployeeRecord
                emp = db.query(EmployeeRecord).filter(
                    EmployeeRecord.id == issue.employee_record_id,
                ).first()
                if emp:
                    emp.status = "IGNORED"
        else:
            issue.status = "RESOLVED"

        issue.resolve_action = action
        issue.resolved_by = "admin"
        issue.resolved_at = datetime.now()
        db.commit()

        return {"issue_id": issue.id, "status": issue.status}
    except BizError:
        raise
    finally:
        db.close()


def _issue_to_dict(issue: CheckIssue) -> dict:
    return {
        "issue_id": issue.id,
        "level": issue.level,
        "issue_code": issue.issue_code,
        "message": issue.message,
        "employee_name": "",
        "field_code": issue.field_code,
        "status": issue.status,
    }
