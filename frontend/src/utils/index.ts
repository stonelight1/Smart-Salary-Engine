/* ======= Smart Salary Engine 前端工具函数 ======= */

/**
 * 格式：金额 → "12,345.67"
 */
export function formatMoney(val: string | number | undefined | null): string {
  if (val === null || val === undefined || val === '') return '-'
  if (typeof val === 'string' && val.trim() === '') return '-'
  const num = Number(val)
  if (isNaN(num)) return '-'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/**
 * 格式：ISO 日期字符串 → "2026-07-11 14:19"
 */
export function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${mi}`
}

/**
 * 格式："2026-07" → "2026年7月"
 */
export function formatMonth(month: string | undefined | null): string {
  if (!month) return '-'
  const parts = month.split('-')
  if (parts.length === 2) {
    return `${parts[0]}年${parseInt(parts[1], 10)}月`
  }
  return month
}

/** 任务状态 → 中文 */
export const STATUS_LABEL: Record<string, string> = {
  CREATED: '待导入',
  IMPORTING: '导入中',
  IMPORTED: '已导入',
  CHECKING: '检查中',
  CHECK_FAILED: '检查未通过',
  CHECK_PASSED: '检查通过',
  CALCULATING: '计算中',
  CALCULATED: '已计算',
  CONFIRMED: '已确认',
  LOCKED: '已锁定',
  EXPORTED: '已导出',
  FAILED: '处理失败',
  VOIDED: '已作废',
}

/** Element Plus tag type 映射 */
export const STATUS_TAG: Record<string, string> = {
  CREATED: 'info',
  IMPORTING: 'warning',
  IMPORTED: 'primary',
  CHECKING: 'warning',
  CHECK_FAILED: 'danger',
  CHECK_PASSED: 'success',
  CALCULATING: 'warning',
  CALCULATED: 'success',
  CONFIRMED: 'success',
  LOCKED: 'info',
  EXPORTED: 'success',
  FAILED: 'danger',
  VOIDED: 'info',
}

export function statusLabel(s: string | undefined): string {
  return STATUS_LABEL[s ?? ''] || s || '-'
}

export function statusTag(s: string | undefined): string {
  return STATUS_TAG[s ?? ''] || 'info'
}

/** 异常等级 → 中文 */
export const ISSUE_LABEL: Record<string, string> = {
  BLOCK: '阻断',
  WARN: '警告',
  INFO: '提示',
}

/** 异常状态 → 中文 */
export const ISSUE_STATUS_LABEL: Record<string, string> = {
  OPEN: '待处理',
  RESOLVED: '已解决',
  IGNORED: '已忽略',
}

/** 员工状态 → 中文 */
export const EMP_STATUS_LABEL: Record<string, string> = {
  NORMAL: '正常',
  NAME_DUPLICATE: '重名',
  IGNORED: '已忽略',
}

/** 导出 API 返回文件 ID → 触发下载 */
export function downloadExportFile(exportFileId: string) {
  const base = import.meta.env.VITE_API_BASE || ''
  const url = `${base}/api/v1/export-files/${exportFileId}/download`
  fetch(url)
    .then((r) => {
      if (!r.ok) throw new Error('下载失败')
      return r.blob()
    })
    .then((blob) => {
      const filename = `export_${exportFileId}.xlsx`
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(blobUrl)
    })
    .catch(() => {
      window.open(url, '_blank')
    })
}

/** 任务状态中文映射（兼容旧字段名） */
export const TASK_STEP_LABEL: Record<string, string> = {
  CREATED: '待导入',
  IMPORTING: '导入中',
  IMPORTED: '已导入',
  CHECKING: '检查中',
  CHECK_FAILED: '异常处理',
  CHECK_PASSED: '检查通过',
  CALCULATING: '计算中',
  CALCULATED: '已计算',
  CONFIRMED: '已确认',
  LOCKED: '已锁定',
  EXPORTED: '已导出',
  FAILED: '处理失败',
  VOIDED: '已作废',
}

/**
 * 判断任务是否可进行某步骤（基于状态）
 */
export function canStep(run: { status: string } | null, step: string): boolean {
  if (!run) return false
  const order = [
    'CREATED', 'IMPORTING', 'IMPORTED', 'CHECKING',
    'CHECK_FAILED', 'CHECK_PASSED', 'CALCULATING',
    'CALCULATED', 'CONFIRMED', 'LOCKED', 'EXPORTED', 'FAILED', 'VOIDED',
  ]
  const stepMap: Record<string, number> = {
    import: 0,
    confirm: 1,
    check: 2,
    issues: 3,
    calculate: 4,
    explain: 5,
    export: 6,
  }
  const cur = order.indexOf(run.status)
  const need = stepMap[step] ?? -1
  return cur >= need
}

/* ======= 核算流程阶段映射 ======= */

/** 六阶段流程定义 */
export const PROCESS_STAGES = [
  { key: 'import', label: '数据导入', icon: 'UploadFilled', desc: '上传工资数据文件' },
  { key: 'check', label: '异常检查', icon: 'WarningFilled', desc: '检查数据完整性与正确性' },
  { key: 'calculate', label: '工资计算', icon: 'Coin', desc: '执行工资公式计算' },
  { key: 'review', label: '人工审核', icon: 'CircleCheck', desc: '审核确认工资数据' },
  { key: 'export', label: '结果导出', icon: 'Download', desc: '导出最终工资结果' },
  { key: 'done', label: '已完成', icon: 'Flag', desc: '核算流程全部完成' },
]

/** 任务状态 → 流程阶段索引 */
export const STATUS_TO_STAGE: Record<string, number> = {
  CREATED: 0,
  IMPORTING: 0,
  IMPORTED: 0,
  CHECKING: 1,
  CHECK_FAILED: 1,
  CHECK_PASSED: 2,
  CALCULATING: 2,
  CALCULATED: 2,
  CONFIRMED: 3,
  EXPORTED: 4,
  LOCKED: 5,
  VOIDED: 5,
}

export function getStageIndex(status: string | undefined): number {
  if (!status) return 0
  const idx = STATUS_TO_STAGE[status]
  return idx ?? 0
}

export function getStageKey(status: string | undefined): string {
  const idx = getStageIndex(status)
  return PROCESS_STAGES[idx]?.key || 'import'
}

/** 状态 → 行操作按钮文字 */
export function getActionLabel(status: string | undefined): string {
  const map: Record<string, string> = {
    CREATED: '开始导入',
    IMPORTING: '导入中',
    IMPORTED: '数据检查',
    CHECKING: '检查中',
    CHECK_FAILED: '处理异常',
    CHECK_PASSED: '开始计算',
    CALCULATING: '计算中',
    CALCULATED: '查看工资',
    CONFIRMED: '结果导出',
    LOCKED: '查看详情',
    EXPORTED: '下载结果',
    FAILED: '重新处理',
    VOIDED: '查看详情',
  }
  return map[status ?? ''] || '查看详情'
}
