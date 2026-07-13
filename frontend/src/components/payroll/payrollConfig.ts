/** ==============================================
 *  Smart Salary Engine — 工资核算工作台集中配置
 *  状态映射、阶段映射、操作权限映射统一管理
 *  ============================================== */

/** 核算流程阶段 */
export const PROCESS_STAGES = [
  { key: 'import', label: '数据导入' },
  { key: 'check', label: '异常检查' },
  { key: 'calculate', label: '工资计算' },
  { key: 'review', label: '人工审核' },
  { key: 'export', label: '结果导出' },
  { key: 'done', label: '已完成' },
] as const

/** 任务状态 → 阶段索引 */
export const STATUS_TO_STAGE: Record<string, number> = {
  CREATED: 0,
  IMPORTING: 0,
  IMPORTED: 0,
  CHECKING: 1,
  CHECK_FAILED: 1,
  CHECK_PASSED: 1,
  CALCULATING: 2,
  CALCULATED: 2,
  CONFIRMED: 3,
  EXPORTED: 4,
  LOCKED: 5,
  FAILED: 5,
  VOIDED: 5,
}

export function getStageIndex(status: string): number {
  return STATUS_TO_STAGE[status] ?? 0
}

/** 状态配置完整定义 */
export interface StatusConfig {
  label: string
  tone: 'neutral' | 'processing' | 'success' | 'danger' | 'warning' | 'info' | 'muted'
  action: string
}

/**
 * 一条状态的所有展示配置：
 * - label: 中文状态名
 * - tone: 色调度（用于小圆点和文字色）
 * - action: 行操作主按钮文案
 */
export const STATUS_CONFIG: Record<string, StatusConfig> = {
  CREATED:      { label: '待导入',     tone: 'neutral',    action: '开始导入' },
  IMPORTING:    { label: '导入中',     tone: 'processing', action: '导入中' },
  IMPORTED:     { label: '已导入',     tone: 'info',       action: '数据检查' },
  CHECKING:     { label: '检查中',     tone: 'processing', action: '检查中' },
  CHECK_FAILED: { label: '检查未通过', tone: 'danger',     action: '处理异常' },
  CHECK_PASSED: { label: '检查通过',   tone: 'success',    action: '开始计算' },
  CALCULATING:  { label: '计算中',     tone: 'processing', action: '计算中' },
  CALCULATED:   { label: '已计算',     tone: 'success',    action: '查看工资' },
  CONFIRMED:    { label: '已确认',     tone: 'success',    action: '结果导出' },
  LOCKED:       { label: '已锁定',     tone: 'muted',      action: '查看详情' },
  EXPORTED:     { label: '已导出',     tone: 'success',    action: '下载结果' },
  FAILED:       { label: '处理失败',   tone: 'danger',     action: '重新处理' },
  VOIDED:       { label: '已作废',     tone: 'muted',      action: '查看详情' },
}

/** 获取状态配置（含降级） */
export function getStatusConfig(status: string): StatusConfig {
  return STATUS_CONFIG[status] ?? { label: status, tone: 'neutral', action: '查看详情' }
}

/** 处理中状态集合（用于概览统计） */
export const PROCESSING_STATUSES = new Set([
  'CREATED', 'IMPORTING', 'IMPORTED', 'CHECKING', 'CHECK_FAILED',
  'CHECK_PASSED', 'CALCULATING', 'CALCULATED',
])

/** 异常状态集合 */
export const ABNORMAL_STATUSES = new Set(['CHECK_FAILED', 'FAILED'])

/** 已完成状态集合 */
export const COMPLETED_STATUSES = new Set(['EXPORTED', 'LOCKED'])

/* ---- 操作权限判定 ---- */

/** 可删除：仅空任务（CREATED） */
export function canDelete(status: string): boolean {
  return status === 'CREATED'
}

/** 可作废：非运行中、非已作废、非已锁定、非已导出、非 CREATED */
export function canVoid(status: string): boolean {
  if (['IMPORTING', 'CHECKING', 'CALCULATING', 'VOIDED', 'LOCKED', 'EXPORTED', 'CREATED'].includes(status)) return false
  return true
}

/** 可归档：已导出、已锁定、已作废、处理失败 */
export function canArchive(status: string): boolean {
  return ['EXPORTED', 'LOCKED', 'VOIDED', 'FAILED'].includes(status)
}

/* ---- 色调度 → CSS 变量映射（保持与 style.css 一致） ---- */
export const TONE_COLORS: Record<string, { dot: string; text: string; bg: string }> = {
  neutral:    { dot: '#9CA3AF', text: '#6B7280', bg: '#F3F4F6' },
  processing: { dot: '#2563EB', text: '#2563EB', bg: '#EFF6FF' },
  success:    { dot: '#16A34A', text: '#16A34A', bg: '#F0FDF4' },
  danger:     { dot: '#DC2626', text: '#DC2626', bg: '#FEF2F2' },
  warning:    { dot: '#D97706', text: '#D97706', bg: '#FFFBEB' },
  info:       { dot: '#2563EB', text: '#2563EB', bg: '#EFF6FF' },
  muted:      { dot: '#D1D5DB', text: '#9CA3AF', bg: '#F9FAFB' },
}
