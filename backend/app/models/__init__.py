"""SQLAlchemy ORM 模型定义 — 薪资核算系统 V2"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SalaryRun(Base):
    __tablename__ = "salary_run"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="任务 ID")
    name: Mapped[str] = mapped_column(String(255), comment="任务名称")
    payroll_month: Mapped[str] = mapped_column(String(7), comment="工资月份 YYYY-MM")
    status: Mapped[str] = mapped_column(String(32), default="CREATED", comment="任务状态")
    current_calc_version: Mapped[int] = mapped_column(Integer, default=0, comment="当前计算版本")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_by: Mapped[str] = mapped_column(String(64), comment="创建人")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 引用信息
    reference_run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="引用系统版本任务 ID")
    reference_source_type: Mapped[str] = mapped_column(String(20), default="SYSTEM_FINAL", comment="SYSTEM_FINAL / EXTERNAL_EXCEL / NONE")
    reference_external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="外部引用版本 ID")
    run_version: Mapped[str] = mapped_column(String(16), default="DRAFT", comment="DRAFT / FINAL")

    # 软删除
    delete_flag: Mapped[int] = mapped_column(Integer, default=0, comment="软删除标记 0=正常 1=已删除")
    deleted_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="删除人")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="删除时间")
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="作废原因")
    voided_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="作废人")
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="作废时间")
    archive_flag: Mapped[int] = mapped_column(Integer, default=0, comment="归档标记 0=正常 1=已归档")
    archived_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="归档人")
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="归档时间")


class ImportBatch(Base):
    __tablename__ = "import_batch"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    file_id: Mapped[str] = mapped_column(String(64))
    file_role: Mapped[str] = mapped_column(String(32), default="MAIN")
    status: Mapped[str] = mapped_column(String(32), default="PARSED")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkbookFile(Base):
    __tablename__ = "workbook_file"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    original_name: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    file_size: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SheetMapping(Base):
    __tablename__ = "sheet_mapping"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_batch_id: Mapped[str] = mapped_column(String(64), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255))
    sheet_type: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column()
    need_confirm: Mapped[bool] = mapped_column(default=False)
    header_row_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ColumnMapping(Base):
    __tablename__ = "column_mapping"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sheet_mapping_id: Mapped[str] = mapped_column(String(64), index=True)
    original_column: Mapped[str] = mapped_column(String(255))
    field_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    field_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column()
    need_confirm: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmployeeRecord(Base):
    __tablename__ = "employee_record"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="NORMAL")
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_standard: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    basic_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    performance_salary_standard: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    performance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    performance_score_source: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    performance_salary_actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    attendance_rule_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    attendance_rule_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    standard_attendance_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    leave_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    actual_attendance_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    attendance_deduction: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    gross_salary_before_attendance: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class EmployeeFieldValue(Base):
    __tablename__ = "employee_field_value"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_record_id: Mapped[str] = mapped_column(String(64), index=True)
    field_code: Mapped[str] = mapped_column(String(64))
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_decimal: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 6), nullable=True)
    value_type: Mapped[str] = mapped_column(String(32))
    source_file_id: Mapped[str] = mapped_column(String(64))
    source_sheet: Mapped[str] = mapped_column(String(255))
    source_row: Mapped[int] = mapped_column(Integer)
    source_column: Mapped[str] = mapped_column(String(255))
    import_batch_id: Mapped[str] = mapped_column(String(64))
    is_manual: Mapped[bool] = mapped_column(default=False)
    manual_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manual_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    manual_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CheckIssue(Base):
    __tablename__ = "check_issue"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_record_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    issue_code: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(16))
    field_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    resolve_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CalculationResult(Base):
    __tablename__ = "calculation_result"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_record_id: Mapped[str] = mapped_column(String(64))
    calc_version: Mapped[int] = mapped_column(Integer)
    item_code: Mapped[str] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(128))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    formula: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CalculationTrace(Base):
    __tablename__ = "calculation_trace"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    calculation_result_id: Mapped[str] = mapped_column(String(64), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    expression: Mapped[str] = mapped_column(Text)
    input_values_json: Mapped[str] = mapped_column(Text)
    result_value: Mapped[str] = mapped_column(String(255))
    source_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ExportFile(Base):
    __tablename__ = "export_file"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    calc_version: Mapped[int] = mapped_column(Integer)
    template_file_id: Mapped[str] = mapped_column(String(64))
    file_name: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="HR")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdjustmentItem(Base):
    __tablename__ = "adjustment_item"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_record_id: Mapped[str] = mapped_column(String(64))
    field_code: Mapped[str] = mapped_column(String(64))
    adjustment_type: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    reverted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reverted_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text)
    operator: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PerformanceImportRecord(Base):
    __tablename__ = "performance_import_record"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_record_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    parse_method: Mapped[str] = mapped_column(String(32))
    batch_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="MATCHED")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LeaveImportRecord(Base):
    __tablename__ = "leave_import_record"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_record_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    leave_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    leave_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    leave_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    leave_days: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    leave_type: Mapped[str] = mapped_column(String(64), default="")
    approval_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="MATCHED")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
#  新增：外部引用版本
# ============================================================

class SalaryReferenceSource(Base):
    """
    工资引用版本 — 外部 Excel 解析后的引用快照。
    用于存储上传的上月最终工资表解析结果。
    """
    __tablename__ = "salary_reference_source"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="引用版本 ID")
    source_type: Mapped[str] = mapped_column(String(20), default="EXTERNAL_EXCEL", comment="EXTERNAL_EXCEL")

    # 月份关联
    reference_salary_month: Mapped[str] = mapped_column(String(7), comment="引用工资月份 YYYY-MM")
    target_salary_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, comment="目标工资月份")

    # 文件信息
    original_file_name: Mapped[str] = mapped_column(String(512), comment="原始文件名")
    file_storage_path: Mapped[str] = mapped_column(String(1024), comment="文件存储路径")
    file_hash: Mapped[str] = mapped_column(String(64), comment="文件 SHA-256 哈希")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小")

    # 工作表
    sheet_name: Mapped[str] = mapped_column(String(255), default="", comment="识别的工作表名称")

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING_CONFIRM", comment="PARSING / PENDING_CONFIRM / CONFIRMED / FAILED")

    # 解析统计
    employee_count: Mapped[int] = mapped_column(Integer, default=0, comment="有效员工数")
    summary_row_count: Mapped[int] = mapped_column(Integer, default=0, comment="汇总行数")
    empty_row_count: Mapped[int] = mapped_column(Integer, default=0, comment="空白行数")
    invalid_row_count: Mapped[int] = mapped_column(Integer, default=0, comment="异常行数")

    # 字段映射 JSON
    field_mapping_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="字段映射 JSON")
    # 解析结果 JSON（员工快照）
    parsed_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="解析数据 JSON")

    # 元数据
    created_by: Mapped[str] = mapped_column(String(64), comment="上传人")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="上传时间")
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="确认人")
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="确认时间")


# ============================================================
#  员工档案 + 薪资标准 + 异动 + 快照 + 工资项 (V4)
# ============================================================

class EmployeeMaster(Base):
    """员工档案（长期）"""
    __tablename__ = "employee_master"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resign_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    contact_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SalaryStandard(Base):
    """薪资标准（长期，有效期限）"""
    __tablename__ = "salary_standard"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_master_id: Mapped[str] = mapped_column(String(64), index=True)
    salary_standard: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    basic_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    performance_salary_standard: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmployeePositionHistory(Base):
    """员工岗位/部门异动记录"""
    __tablename__ = "employee_position_history"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_master_id: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date)
    change_type: Mapped[str] = mapped_column(String(32))
    prev_department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prev_position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MonthlySalarySnapshot(Base):
    """月度工资快照（创建后不受档案变更影响）"""
    __tablename__ = "monthly_salary_snapshot"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    employee_master_id: Mapped[str] = mapped_column(String(64))
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_standard: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    basic_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    performance_salary_standard: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    performance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True, default=Decimal("1.0"))
    performance_score_source: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, default="DEFAULT")
    performance_salary_actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    attendance_rule_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    attendance_rule_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    standard_attendance_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    leave_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True, default=Decimal("0"))
    actual_attendance_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    attendance_deduction: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    gross_salary_before_attendance: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    gross_salary_after_attendance: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    net_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SalaryItemDetail(Base):
    """工资项目明细（可扩展的 EARNING / DEDUCTION / COMPANY_COST）"""
    __tablename__ = "salary_item_detail"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    salary_run_id: Mapped[str] = mapped_column(String(64), index=True)
    item_type: Mapped[str] = mapped_column(String(16))
    item_code: Mapped[str] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(128))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    source: Mapped[str] = mapped_column(String(32), default="SYSTEM")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
#  员工异动 + 任职历史 (V5)
# ============================================================

class EmployeeAssignmentHistory(Base):
    """员工任职历史"""
    __tablename__ = "employee_assignment_history"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_master_id: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    effective_start_date: Mapped[date] = mapped_column(Date)
    effective_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    change_type: Mapped[str] = mapped_column(String(32))
    change_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_batch_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmployeeChangeCandidate(Base):
    """员工异动待确认记录"""
    __tablename__ = "employee_change_candidate"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salary_month: Mapped[str] = mapped_column(String(7))
    employee_master_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    candidate_type: Mapped[str] = mapped_column(String(32))
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    old_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_batch_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    handled_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    handle_remark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
