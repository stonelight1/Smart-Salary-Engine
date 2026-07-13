export interface RunStatusInfo {
  id: string
  name: string
  payroll_month: string
  status: string
  block_count: number
  warn_count: number
  current_calc_version: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface SheetMappingItem {
  sheet_mapping_id: string
  sheet_name: string
  sheet_type: string
  confidence: number
  need_confirm: boolean
  row_count: number
  header_row_index: number | null
}

export interface ColumnMappingItem {
  column_mapping_id: string
  original_column: string
  field_code: string | null
  field_name: string | null
  confidence: number
  need_confirm: boolean
}

export interface IssueItem {
  issue_id: string
  level: 'BLOCK' | 'WARN' | 'INFO'
  issue_code: string
  message: string
  employee_name: string | null
  field_code: string | null
  status: 'OPEN' | 'RESOLVED' | 'IGNORED'
}

export interface EmployeeItem {
  employee_ref_id: string
  employee_name: string
  status: string
  fields: Record<string, string>
  issue_count: number
}

export type RunStatus =
  | 'CREATED'
  | 'IMPORTING'
  | 'IMPORTED'
  | 'CHECKING'
  | 'CHECK_FAILED'
  | 'CHECK_PASSED'
  | 'CALCULATING'
  | 'CALCULATED'
  | 'EXPORTED'
  | 'FAILED'
