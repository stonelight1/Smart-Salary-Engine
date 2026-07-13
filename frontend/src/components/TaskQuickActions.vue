<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  runId: string
  run: any
}>()

const router = useRouter()

type ActionState = 'recommended' | 'normal' | 'done' | 'disabled'

interface ActionCard {
  key: string
  title: string
  description: string
  icon: string
  state: ActionState
  disabledReason?: string
  onClick: () => void
}

const actions = computed<ActionCard[]>(() => {
  const r = props.run
  if (!r) return []
  const s: string = r.status
  const version: number = r.current_calc_version ?? 0
  const hasCalc = version > 0

  return [
    {
      key: 'import',
      title: '导入 Excel',
      description: '上传员工基础薪资、考勤、绩效等数据',
      icon: 'UploadFilled',
      state: getImportState(s),
      disabledReason: '导入进行中',
      onClick: () => router.push({ name: 'RunImport', params: { runId: props.runId } }),
    },
    {
      key: 'check',
      title: getCheckTitle(s),
      description: getCheckDesc(s),
      icon: getCheckIcon(s),
      state: getCheckState(s, hasCalc),
      disabledReason: '请先完成 Excel 数据导入',
      onClick: handleCheckClick,
    },
    {
      key: 'explain',
      title: '工资解释',
      description: '查看员工实发工资的计算说明',
      icon: 'Reading',
      state: getExplainState(s, hasCalc),
      disabledReason: '需先完成工资计算',
      onClick: () => router.push({ name: 'RunExplain', params: { runId: props.runId } }),
    },
    {
      key: 'export',
      title: getExportTitle(s, hasCalc),
      description: '导出最终工资核算结果文件',
      icon: 'Download',
      state: getExportState(s, hasCalc),
      disabledReason: '需先完成工资计算',
      onClick: handleExportClick,
    },
  ]
})

/* ---- 导入 ---- */
function getImportState(s: string): ActionState {
  if (['CREATED', 'FAILED'].includes(s)) return 'recommended'
  if (s === 'IMPORTING') return 'disabled'
  return 'done'
}

/* ---- 检查 ---- */
function getCheckTitle(s: string): string {
  if (s === 'CHECK_FAILED') return '异常处理'
  if (['CHECK_PASSED', 'CALCULATING', 'CALCULATED', 'EXPORTED'].includes(s)) return '数据检查'
  return '数据检查'
}

function getCheckDesc(s: string): string {
  if (s === 'CREATED') return '检查缺失项、异常值和格式问题'
  if (s === 'IMPORTING') return '请等待数据导入完成'
  if (s === 'IMPORTED') return '检查缺失项、异常值和格式问题'
  if (s === 'CHECK_FAILED') return '发现阻断异常，需人工核实处理'
  if (s === 'CHECK_PASSED') return '检查通过，数据完整且格式正确'
  if (['CALCULATING', 'CALCULATED', 'EXPORTED'].includes(s)) return '数据校验已完成，结果正常'
  return '查看当前数据校验结果'
}

function getCheckIcon(s: string): string {
  if (s === 'CHECK_FAILED') return 'WarningFilled'
  return 'Select'
}

function getCheckState(s: string, _hasCalc: boolean): ActionState {
  if (['CREATED', 'IMPORTING', 'FAILED'].includes(s)) return 'disabled'
  if (s === 'IMPORTED') return 'recommended'
  if (s === 'CHECK_FAILED') return 'recommended'
  return 'done'
}

function handleCheckClick() {
  const s = props.run?.status
  if (['CREATED', 'IMPORTING', 'FAILED'].includes(s)) return
  if (s === 'CHECK_FAILED') {
    router.push({ name: 'RunIssues', params: { runId: props.runId } })
  } else {
    router.push({ name: 'RunCheck', params: { runId: props.runId } })
  }
}

/* ---- 解释 ---- */
function getExplainState(s: string, hasCalc: boolean): ActionState {
  if (!hasCalc && ['CALCULATED', 'EXPORTED'].includes(s)) return 'disabled'
  if (!hasCalc) return 'disabled'
  if (s === 'CALCULATED') return 'recommended'
  return 'normal'
}

/* ---- 导出 ---- */
function getExportTitle(s: string, hasCalc: boolean): string {
  if (s === 'EXPORTED') return '下载工资表'
  if (!hasCalc) return '导出结果'
  return '导出结果'
}

function getExportState(s: string, hasCalc: boolean): ActionState {
  if (!hasCalc) return 'disabled'
  if (s === 'EXPORTED') return 'recommended'
  return 'normal'
}

function handleExportClick() {
  const s = props.run?.status
  if (s === 'EXPORTED') {
    router.push({ name: 'RunExport', params: { runId: props.runId } })
  } else {
    const version = props.run?.current_calc_version ?? 0
    if (version > 0) {
      router.push({ name: 'RunExport', params: { runId: props.runId } })
    }
  }
}

/** 获取当前状态对应的推荐操作文案 */
const currentStatusHint = computed(() => {
  const s = props.run?.status
  const map: Record<string, string> = {
    CREATED: '当前状态：待导入 — 下一步推荐「上传员工基础薪资」',
    IMPORTED: '当前状态：已导入 — 下一步推荐「数据检查」',
    CHECK_FAILED: '当前状态：检查未通过 — 需先处理异常',
    CHECK_PASSED: '当前状态：检查通过 — 下一步推荐「工资计算」',
    CALCULATED: '当前状态：已计算 — 可确认数据或查看解释',
    CONFIRMED: '当前状态：已确认 — 可锁定批次防止误改',
    LOCKED: '当前状态：已锁定 — 需解锁后才能修改',
    EXPORTED: '当前状态：已导出 — 可下载工资表或查看解释',
    FAILED: '当前状态：处理失败 — 建议重新导入数据',
  }
  return map[s ?? ''] || ''
})
</script>

<template>
  <div class="quick-actions-card" v-if="run">
    <div class="quick-actions-header">
      <div class="quick-actions-title-group">
        <span class="quick-actions-title">快捷操作</span>
        <span class="quick-actions-subtitle">{{ currentStatusHint }}</span>
      </div>
    </div>
    <div class="action-cards-grid">
      <div
        v-for="action in actions"
        :key="action.key"
        class="action-card"
        :class="[
          `action-${action.state}`,
          { 'action-clickable': action.state !== 'disabled' },
        ]"
        @click="action.state !== 'disabled' && action.onClick()"
      >
        <!-- 左上角状态标签 -->
        <div class="action-card-badges">
          <span v-if="action.state === 'recommended'" class="action-badge badge-recommended">推荐操作</span>
          <span v-if="action.state === 'done'" class="action-badge badge-done">
            <el-icon :size="12"><Check /></el-icon>
            已完成
          </span>
        </div>

        <!-- 图标 -->
        <div class="action-icon-wrapper" :class="`icon-${action.state}`">
          <el-icon :size="22">
            <component :is="action.icon" />
          </el-icon>
        </div>

        <!-- 文字内容 -->
        <div class="action-card-body">
          <div class="action-card-title">{{ action.title }}</div>
          <div class="action-card-desc">{{ action.description }}</div>
        </div>

        <!-- 不可用遮罩 -->
        <div v-if="action.state === 'disabled'" class="action-disabled-overlay">
          <span class="disabled-reason">{{ action.disabledReason }}</span>
        </div>

        <!-- 进入箭头 -->
        <div v-if="action.state !== 'disabled'" class="action-arrow">
          <el-icon :size="16"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-actions-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  padding: 20px;
}

.quick-actions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.quick-actions-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-actions-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.quick-actions-subtitle {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ---- 操作卡片网格 ---- */
.action-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.action-card {
  position: relative;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
  overflow: hidden;
}

.action-card.action-clickable {
  cursor: pointer;
}

.action-card.action-clickable:hover {
  border-color: #D1D5DB;
  background: #FAFBFC;
}

/* ---- 不同状态 ---- */

/* 推荐操作 */
.action-card.action-recommended {
  border-color: var(--primary);
  background: var(--primary-light);
}

.action-card.action-recommended:hover {
  border-color: var(--primary-hover);
  background: #DBEAFE;
  box-shadow: 0 1px 6px rgba(37, 99, 235, 0.08);
}

/* 已完成 */
.action-card.action-done {
  background: #FAFBFC;
}

.action-card.action-done:hover {
  border-color: #D1D5DB;
}

/* 不可用 */
.action-card.action-disabled {
  background: #F9FAFB;
  cursor: not-allowed;
  opacity: 0.55;
}

/* ---- 徽标 ---- */
.action-card-badges {
  display: flex;
  gap: 6px;
  min-height: 20px;
  margin-bottom: 8px;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 4px;
  font-weight: 500;
  line-height: 18px;
}

.badge-recommended {
  background: #DBEAFE;
  color: var(--primary);
}

.badge-done {
  background: var(--success-light);
  color: var(--success);
}

/* ---- 图标 ---- */
.action-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.icon-recommended {
  background: #DBEAFE;
  color: var(--primary);
}

.icon-done {
  background: var(--success-light);
  color: var(--success);
}

.icon-normal {
  background: #F3F4F6;
  color: var(--text-secondary);
}

.icon-disabled {
  background: #F3F4F6;
  color: var(--text-tertiary);
}

/* ---- 文字 ---- */
.action-card-body {
  flex: 1;
}

.action-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.action-done .action-card-title {
  color: var(--text-secondary);
}

.action-disabled .action-card-title {
  color: var(--text-tertiary);
}

.action-card-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  line-height: 1.4;
}

.action-done .action-card-desc {
  color: var(--text-tertiary);
}

/* ---- 箭头 ---- */
.action-arrow {
  position: absolute;
  right: 12px;
  top: 16px;
  color: var(--text-tertiary);
  transition: transform 0.15s;
}

.action-card:hover .action-arrow {
  transform: translateX(2px);
}

.action-recommended .action-arrow {
  color: var(--primary);
}

/* ---- 不可用遮罩 ---- */
.action-disabled-overlay {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 12px;
  pointer-events: none;
}

.disabled-reason {
  font-size: 12px;
  color: var(--text-tertiary);
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 10px;
  border-radius: 4px;
}

/* ---- 响应式 ---- */
@media (max-width: 1100px) {
  .action-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .action-cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
