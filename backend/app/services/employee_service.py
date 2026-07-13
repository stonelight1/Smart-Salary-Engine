"""
员工档案管理服务
"""

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import (
    EmployeeMaster, SalaryStandard, EmployeePositionHistory
)

logger = logging.getLogger(__name__)


def generate_id(prefix="") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def list_employees(page=1, page_size=20, keyword="", include_resigned=False, status="") -> dict:
    db = SessionLocal()
    try:
        query = db.query(EmployeeMaster)

        # 状态筛选逻辑
        if status == "ACTIVE":
            query = query.filter(EmployeeMaster.status == "ACTIVE")
        elif status == "RESIGNED":
            query = query.filter(EmployeeMaster.status.in_(["RESIGNED", "TERMINATED"]))
        elif not include_resigned:
            # 默认只显示在职
            query = query.filter(EmployeeMaster.status == "ACTIVE")

        # 排除无效员工（None, null, 空字符串等）
        query = query.filter(
            EmployeeMaster.employee_name.isnot(None),
            EmployeeMaster.employee_name != "",
            EmployeeMaster.employee_name != "None",
            EmployeeMaster.employee_name != "null",
            EmployeeMaster.employee_name != "undefined",
        )

        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                EmployeeMaster.employee_name.like(kw) | EmployeeMaster.employee_no.like(kw)
            )
        query = query.order_by(EmployeeMaster.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for emp in items:
            ss = db.query(SalaryStandard).filter(
                SalaryStandard.employee_master_id == emp.id,
                SalaryStandard.end_date.is_(None),
            ).first()
            result.append({
                "id": emp.id,
                "employee_no": emp.employee_no or "",
                "employee_name": emp.employee_name,
                "department": emp.department or "",
                "position": emp.position or "",
                "status": emp.status,
                "hire_date": emp.hire_date.isoformat() if emp.hire_date else "",
                "resign_date": emp.resign_date.isoformat() if emp.resign_date else "",
                "salary_standard": float(ss.salary_standard) if ss else None,
                "basic_salary": float(ss.basic_salary) if ss else None,
                "performance_salary_standard": float(ss.performance_salary_standard) if ss else None,
                "contact_info": emp.contact_info or "",
                "remark": emp.remark or "",
            })
        return {"items": result, "total": total}
    finally:
        db.close()


def get_employee(employee_id: str) -> dict:
    db = SessionLocal()
    try:
        emp = db.query(EmployeeMaster).filter(EmployeeMaster.id == employee_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")
        ss_list = db.query(SalaryStandard).filter(
            SalaryStandard.employee_master_id == emp.id,
        ).order_by(SalaryStandard.effective_date.desc()).all()
        pos_list = db.query(EmployeePositionHistory).filter(
            EmployeePositionHistory.employee_master_id == emp.id,
        ).order_by(EmployeePositionHistory.effective_date.desc()).all()
        return {
            "id": emp.id,
            "employee_no": emp.employee_no or "",
            "employee_name": emp.employee_name,
            "department": emp.department or "",
            "position": emp.position or "",
            "status": emp.status,
            "hire_date": emp.hire_date.isoformat() if emp.hire_date else "",
            "resign_date": emp.resign_date.isoformat() if emp.resign_date else "",
            "contact_info": emp.contact_info or "",
            "remark": emp.remark or "",
            "salary_history": [
                {
                    "id": s.id,
                    "salary_standard": float(s.salary_standard),
                    "basic_salary": float(s.basic_salary),
                    "performance_salary_standard": float(s.performance_salary_standard),
                    "effective_date": s.effective_date.isoformat(),
                    "end_date": s.end_date.isoformat() if s.end_date else None,
                    "change_reason": s.change_reason or "",
                } for s in ss_list
            ],
            "position_history": [
                {
                    "id": h.id,
                    "department": h.department,
                    "position": h.position,
                    "effective_date": h.effective_date.isoformat(),
                    "change_type": h.change_type,
                    "change_reason": h.change_reason or "",
                } for h in pos_list
            ],
        }
    finally:
        db.close()


def create_employee(data: dict, created_by: str) -> dict:
    db = SessionLocal()
    try:
        emp_id = generate_id("emp_")
        emp = EmployeeMaster(
            id=emp_id,
            employee_no=_unique_employee_no(db, data.get("employee_no", "")),
            employee_name=data["employee_name"],
            department=data.get("department", ""),
            position=data.get("position", ""),
            hire_date=_parse_date(data.get("hire_date")),
            contact_info=data.get("contact_info", ""),
            remark=data.get("remark", ""),
            status="ACTIVE",
            created_by=created_by,
        )
        db.add(emp)

        # 创建薪资标准
        if data.get("salary_standard"):
            ss = _create_salary_standard(db, emp_id, data, data.get("hire_date"), created_by)
            db.add(ss)
            emp.basic_salary = ss.basic_salary
            emp.performance_salary_standard = ss.performance_salary_standard

        # 创建入职异动记录
        if data.get("hire_date"):
            ph = EmployeePositionHistory(
                id=generate_id("ph_"),
                employee_master_id=emp_id,
                department=data.get("department", ""),
                position=data.get("position", ""),
                effective_date=_parse_date(data["hire_date"]),
                change_type="HIRE",
                change_reason="入职",
                created_by=created_by,
            )
            db.add(ph)

        db.commit()
        return {"id": emp_id, "employee_name": data["employee_name"]}
    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("创建员工失败: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="创建员工失败")
    finally:
        db.close()


def update_employee(employee_id: str, data: dict, created_by: str) -> dict:
    db = SessionLocal()
    try:
        emp = db.query(EmployeeMaster).filter(EmployeeMaster.id == employee_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")

        changes = []

        if "department" in data and data["department"] != emp.department:
            changes.append(f"部门: {emp.department}→{data['department']}")
            emp.department = data["department"]
        if "position" in data and data["position"] != emp.position:
            changes.append(f"岗位: {emp.position}→{data['position']}")
            emp.position = data["position"]

        if "employee_name" in data:
            emp.employee_name = data["employee_name"]
        if "contact_info" in data:
            emp.contact_info = data["contact_info"]
        if "remark" in data:
            emp.remark = data["remark"]

        # 薪资调整
        old_ss = db.query(SalaryStandard).filter(
            SalaryStandard.employee_master_id == emp.id,
            SalaryStandard.end_date.is_(None),
        ).first()

        if data.get("salary_standard") is not None:
            new_val = Decimal(str(data["salary_standard"]))
            if not old_ss or old_ss.salary_standard != new_val:
                if old_ss:
                    old_ss.end_date = date.today()
                new_ss = _create_salary_standard(db, emp.id, data, date.today().isoformat(), created_by)
                db.add(new_ss)
                changes.append(f"薪资: {float(old_ss.salary_standard) if old_ss else 0}→{float(new_val)}")

        # 记录异动
        if changes and ("department" in data or "position" in data):
            ph = EmployeePositionHistory(
                id=generate_id("ph_"),
                employee_master_id=emp.id,
                department=emp.department,
                position=emp.position,
                effective_date=date.today(),
                change_type="TRANSFER",
                change_reason=data.get("change_reason", "; ".join(changes)),
                created_by=created_by,
            )
            db.add(ph)

        db.commit()
        return {"id": emp.id, "updated": True, "changes": changes}
    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("更新员工失败: %s", str(e)[:200], exc_info=True)
        raise BizError(error_code="INTERNAL_ERROR", message="更新员工失败")
    finally:
        db.close()


def resign_employee(employee_id: str, resign_date: str, reason: str, created_by: str) -> dict:
    db = SessionLocal()
    try:
        emp = db.query(EmployeeMaster).filter(EmployeeMaster.id == employee_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")
        if emp.status == "RESIGNED":
            raise BizError(error_code="INVALID_ARGUMENT", message="员工已离职")

        rd = _parse_date(resign_date)
        emp.status = "RESIGNED"
        emp.resign_date = rd

        ph = EmployeePositionHistory(
            id=generate_id("ph_"),
            employee_master_id=emp.id,
            department=emp.department,
            position=emp.position,
            effective_date=rd,
            change_type="RESIGN",
            change_reason=reason or "离职",
            created_by=created_by,
        )
        db.add(ph)

        db.commit()
        return {"id": emp.id, "resign_date": resign_date}
    except BizError:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
#  内部工具函数
# ============================================================

def _unique_employee_no(db, base: str) -> str:
    if not base:
        return f"EMP{uuid.uuid4().hex[:6].upper()}"
    existing = db.query(EmployeeMaster).filter(EmployeeMaster.employee_no == base).first()
    if existing:
        return f"{base}_{uuid.uuid4().hex[:4]}"
    return base


def _create_salary_standard(db, emp_id, data, effective_date_str, created_by) -> SalaryStandard:
    salary_std = Decimal(str(data["salary_standard"]))
    basic = salary_std * Decimal("0.70")
    perf_std = salary_std * Decimal("0.30")
    ss = SalaryStandard(
        id=generate_id("ss_"),
        employee_master_id=emp_id,
        salary_standard=salary_std,
        basic_salary=basic,
        performance_salary_standard=perf_std,
        effective_date=_parse_date(effective_date_str or date.today().isoformat()),
        change_reason=data.get("change_reason", ""),
        created_by=created_by,
    )
    return ss


def _parse_date(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
