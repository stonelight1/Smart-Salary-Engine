import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// 开发环境通过 Vite 代理转发（无 CORS 问题），生产环境通过环境变量配置
const API_BASE = import.meta.env.VITE_API_BASE || ''

const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor - handle common errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    return Promise.reject(error)
  },
)

export default apiClient

// ---- Auth API ----
export const authApi = {
  login(username: string, password: string) {
    return apiClient.post('/auth/login', { username, password })
  },
}

// ---- Salary Run API ----
export const runApi = {
  list(params?: { page?: number; page_size?: number; keyword?: string }) {
    return apiClient.get('/salary-runs', { params })
  },
  create(data: { name: string; payroll_month: string; remark?: string; reference_run_id?: string; run_version?: string; reference_source_type?: string; reference_external_id?: string }) {
    return apiClient.post('/salary-runs', data)
  },
  get(runId: string) {
    return apiClient.get(`/salary-runs/${runId}`)
  },
  confirm(runId: string) {
    return apiClient.post(`/salary-runs/${runId}/confirm`)
  },
  lock(runId: string, reason: string) {
    return apiClient.post(`/salary-runs/${runId}/lock`, { reason })
  },
  unlock(runId: string, reason: string) {
    return apiClient.post(`/salary-runs/${runId}/unlock`, { reason })
  },
  delete(runId: string) {
    return apiClient.post(`/salary-runs/${runId}/delete`)
  },
  void(runId: string, reason: string) {
    return apiClient.post(`/salary-runs/${runId}/void`, { reason })
  },
  archive(runId: string) {
    return apiClient.post(`/salary-runs/${runId}/archive`)
  },
}

// ---- File/Import API ----
export const importApi = {
  getFiles(runId: string) {
    return apiClient.get(`/salary-runs/${runId}/files`)
  },
  upload(runId: string, file: File, fileRole: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('file_role', fileRole)
    return apiClient.post(`/salary-runs/${runId}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getSheets(batchId: string) {
    return apiClient.get(`/import-batches/${batchId}/sheets`)
  },
  getColumns(sheetMappingId: string) {
    return apiClient.get(`/sheet-mappings/${sheetMappingId}/columns`)
  },
  updateSheet(sheetMappingId: string, data: { sheet_type: string; header_row_index?: number }) {
    return apiClient.patch(`/sheet-mappings/${sheetMappingId}`, data)
  },
  updateColumn(columnMappingId: string, data: { field_code: string }) {
    return apiClient.patch(`/column-mappings/${columnMappingId}`, data)
  },
}

// ---- Employee API ----
export const employeeApi = {
  list(runId: string, params?: { page?: number; keyword?: string }) {
    return apiClient.get(`/salary-runs/${runId}/employees`, { params })
  },
  get(employeeRefId: string) {
    return apiClient.get(`/employees/${employeeRefId}`)
  },
  updateField(employeeRefId: string, fieldCode: string, data: { value: string; reason: string }) {
    return apiClient.patch(`/employees/${employeeRefId}/fields/${fieldCode}`, data)
  },
}

// ---- Check API ----
export const checkApi = {
  run(runId: string) {
    return apiClient.post(`/salary-runs/${runId}/check`)
  },
  getIssues(runId: string, params?: { level?: string; status?: string; page?: number }) {
    return apiClient.get(`/salary-runs/${runId}/issues`, { params })
  },
  resolveIssue(issueId: string, data: { action: string; value?: string; reason?: string }) {
    return apiClient.patch(`/issues/${issueId}`, data)
  },
}

// ---- Calculate API ----
export const calcApi = {
  run(runId: string, formulaVersion = 'v1') {
    return apiClient.post(`/salary-runs/${runId}/calculate`, { formula_version: formulaVersion })
  },
  getResults(runId: string, params?: { calc_version?: number; page?: number }) {
    return apiClient.get(`/salary-runs/${runId}/calculation-results`, { params })
  },
  getExplain(runId: string, employeeRefId: string, calcVersion?: number) {
    return apiClient.get(`/salary-runs/${runId}/employees/${employeeRefId}/explain`, {
      params: { calc_version: calcVersion },
    })
  },
}

// ---- Export API ----
export const exportApi = {
  run(runId: string, data: { calc_version: number; include_trace?: boolean; include_issues?: boolean; include_sources?: boolean }) {
    return apiClient.post(`/salary-runs/${runId}/export`, data)
  },
  download(exportFileId: string) {
    return apiClient.get(`/export-files/${exportFileId}/download`, { responseType: 'blob' })
  },
}

// ---- Adjustment API ----
export const adjustmentApi = {
  list(runId: string, employeeId?: string) {
    const params: Record<string, any> = {}
    if (employeeId) params.employee_id = employeeId
    return apiClient.get(`/salary-runs/${runId}/adjustments`, { params })
  },
  create(runId: string, data: {
    employee_record_id: string
    field_code: string
    adjustment_type: string
    amount: string
    reason: string
  }) {
    return apiClient.post(`/salary-runs/${runId}/adjustments`, data)
  },
  revert(adjustmentId: string) {
    return apiClient.post(`/adjustments/${adjustmentId}/revert`)
  },
}

export const configApi = {
  getFields() {
    return apiClient.get('/config/fields')
  },
  getFormulas() {
    return apiClient.get('/config/formulas')
  },
  getCheckRules() {
    return apiClient.get('/config/check-rules')
  },
}
