"""统一 API 响应模型"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel):
    """统一成功响应"""
    success: bool = True
    data: Any = None
    request_id: str = ""


class ApiError(BaseModel):
    """统一错误响应"""
    success: bool = False
    error_code: str
    message: str
    request_id: str = ""
    details: dict[str, Any] = {}


# --- Salary Run ---

class SalaryRunCreate(BaseModel):
    name: str
    payroll_month: str
    remark: str | None = None


class SalaryRunOut(BaseModel):
    id: str
    name: str
    payroll_month: str
    status: str
    remark: str | None = None
    block_count: int = 0
    warn_count: int = 0
    current_calc_version: int = 0
    created_by: str
    created_at: str
    updated_at: str


class SalaryRunList(BaseModel):
    items: list[SalaryRunOut]
    total: int


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: dict[str, Any]


# --- File Import ---

class FileUploadOut(BaseModel):
    import_batch_id: str
    file_id: str
    file_name: str
    status: str
    sheet_count: int
    need_confirm_count: int


# --- Sheet & Column ---

class SheetMappingOut(BaseModel):
    sheet_mapping_id: str
    sheet_name: str
    sheet_type: str
    confidence: float
    need_confirm: bool
    row_count: int
    header_row_index: int | None = None


class SheetMappingUpdate(BaseModel):
    sheet_type: str
    header_row_index: int | None = None
    confirm_remark: str | None = None


class ColumnMappingOut(BaseModel):
    column_mapping_id: str
    original_column: str
    field_code: str | None = None
    field_name: str | None = None
    confidence: float
    need_confirm: bool


class ColumnMappingUpdate(BaseModel):
    field_code: str
    confirm_remark: str | None = None


# --- Employee ---

class EmployeeFieldOut(BaseModel):
    field_code: str
    field_name: str
    value: str | None = None
    source_text: str | None = None


class EmployeeOut(BaseModel):
    employee_ref_id: str
    employee_name: str
    status: str
    fields: dict[str, str]
    issue_count: int = 0


class EmployeeFieldUpdate(BaseModel):
    value: str
    reason: str


# --- Check ---

class CheckResultOut(BaseModel):
    status: str
    block_count: int
    warn_count: int
    info_count: int


class IssueOut(BaseModel):
    issue_id: str
    level: str
    issue_code: str
    message: str
    employee_name: str | None = None
    field_code: str | None = None
    status: str


class IssueResolve(BaseModel):
    action: str
    value: str | None = None
    reason: str | None = None


# --- Calculation ---

class CalculateRequest(BaseModel):
    formula_version: str = "v1"


class CalculateOut(BaseModel):
    status: str
    calc_version: int
    employee_count: int
    success_count: int
    failed_count: int


class CalculationResultOut(BaseModel):
    employee_ref_id: str
    employee_name: str
    gross_salary: str | None = None
    deduction_total: str | None = None
    net_salary: str | None = None


# --- Explain ---

class ExplainInputOut(BaseModel):
    field_code: str
    field_name: str
    value: str
    source_text: str


class ExplainItemOut(BaseModel):
    item_code: str
    item_name: str
    amount: str
    formula: str
    inputs: list[ExplainInputOut]


class ExplainOut(BaseModel):
    employee_name: str
    calc_version: int
    net_salary: str
    summary: str
    items: list[ExplainItemOut]
    warnings: list[str]


# --- Export ---

class ExportRequest(BaseModel):
    calc_version: int
    use_main_workbook_template: bool = True
    include_trace: bool = True
    include_issues: bool = True
    include_sources: bool = True


class ExportOut(BaseModel):
    export_file_id: str
    file_name: str
    download_url: str
