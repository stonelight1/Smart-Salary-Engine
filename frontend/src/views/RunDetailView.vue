<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runApi, calcApi } from '@/api'
import { formatDate, formatMonth, statusLabel, statusTag, formatMoney } from '@/utils'
import TaskQuickActions from '@/components/TaskQuickActions.vue'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string
const run = ref<any>(null)
const loading = ref(false)
const calculationResults = ref<any[]>([])

const steps = [
  { title: '创建任务', key: 'create', route: 'RunDetail' },
  { title: '数据准备', key: 'import', route: 'RunImport' },
  { title: '识别确认', key: 'mapping', route: 'RunMapping' },
  { title: '数据汇总', key: 'summary', route: 'RunDataSummary' },
  { title: '数据检查', key: 'check', route: 'RunCheck' },
  { title: '异常处理', key: 'issues', route: 'RunIssues' },
  { title: '工资计算', key: 'calculate', route: 'RunCalculate' },
  { title: '工资解释', key: 'explain', route: 'RunExplain' },
  { title: '导出', key: 'export', route: 'RunExport' },
]

// 步骤进度计算
const stepStatuses = computed(() => {
  if (!run.value) return steps.map(() => 'wait')
  const s = run.value.status

  // 已导出 → 全部完成
  if (s === 'EXPORTED' || s === 'LOCKED') {
    return steps.map(() => 'success')
  }
  // 失败 → 前序已完成，当前失败
  if (s === 'FAILED') {
    const failedIdx = 1 // 默认在导入
    return steps.map((_, i) => {
      if (i < failedIdx) return 'success'
      if (i === failedIdx) return 'danger'
      return 'wait'
    })
  }

  const statusStepMap: Record<string, number> = {
    CREATED: 0,
    IMPORTING: 0,
    IMPORTED: 2,
    CHECKING: 4,
    CHECK_FAILED: 4,
    CHECK_PASSED: 4,
    CALCULATING: 6,
    CALCULATED: 7,
    CONFIRMED: 8,
    LOCKED: 8,
  }

  // 异常处理状态特殊处理
  let activeIdx = statusStepMap[s] ?? 0
  if (s === 'CHECK_FAILED') {
    // 导入(1)和识别(2)和数据汇总(3)已完成，异常处理是当前步骤（索引5）
    activeIdx = 5
  }

  return steps.map((_, i) => {
    if (i < activeIdx) return 'success'
    if (i === activeIdx) return 'process'
    return 'wait'
  })
})

const currentStepDesc = computed(() => {
  if (!run.value) return ''
  const s = run.value.status
  const map: Record<string, string> = {
    CREATED: '任务已创建，开始导入员工基础薪资等数据',
    IMPORTING: '正在导入数据，请稍候',
    IMPORTED: '数据已导入，请确认数据完整性',
    CHECKING: '正在执行数据检查，请稍候',
    CHECK_FAILED: '检查发现异常，请处理后再计算',
    CHECK_PASSED: '数据检查通过，可以开始工资计算',
    CALCULATING: '正在计算工资，请稍候',
    CALCULATED: '工资计算完成，可以查看工资解释',
    CONFIRMED: '工资数据已确认，可导出或锁定',
    LOCKED: '批次已锁定，数据不可编辑',
    EXPORTED: '工资核算全流程已完成，可下载导出文件',
    FAILED: '处理失败，请检查数据后重试',
  }
  return map[s] || ''
})

const canGoToCheck = computed(() => {
  if (!run.value) return false
  return ['IMPORTED', 'CHECK_FAILED', 'CHECK_PASSED'].includes(run.value.status)
})

const canGoToCalculate = computed(() => {
  if (!run.value) return false
  return ['CHECK_PASSED', 'CALCULATED'].includes(run.value.status)
})

const hasResults = computed(() => (run.value?.current_calc_version ?? 0) > 0)

const isExported = computed(() => ['EXPORTED', 'CONFIRMED', 'LOCKED'].includes(run.value?.status))

onMounted(async () => {
  await loadRun()
})

async function loadRun() {
  loading.value = true
  try {
    const res = await runApi.get(runId)
    run.value = res.data.data
    if ((run.value.current_calc_version ?? 0) > 0) {
      loadResults()
    }
  } catch {
    ElMessage.error('获取任务详情失败')
  } finally {
    loading.value = false
  }
}

async function loadResults() {
  try {
    const res = await calcApi.getResults(runId)
    calculationResults.value = res.data.data.items || []
  } catch { /* ignore */ }
}

function goToStep(step: typeof steps[0], idx: number) {
  // 已完成的步骤可以点击跳转
  if (stepStatuses.value[idx] === 'success' || stepStatuses.value[idx] === 'process') {
    router.push({ name: step.route, params: { runId } })
  }
}

function handleConfirm() {
  ElMessageBox.confirm('确认后数据将被锁定以防止误改，确认执行？', '确认工资数据', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'info',
  }).then(async () => {
    try {
      const res = await runApi.confirm(runId)
      run.value = res.data.data
      ElMessage.success('工资数据已确认')
    } catch (err: any) {
      ElMessage.error(err.response?.data?.message || '确认失败')
    }
  }).catch(() => {})
}

function handleLock() {
  ElMessageBox.prompt('锁定后将不能修改数据，请输入锁定原因', '锁定批次', {
    confirmButtonText: '锁定',
    cancelButtonText: '取消',
    inputPlaceholder: '锁定原因',
  }).then(async ({ value }) => {
    if (!value) { ElMessage.warning('请填写锁定原因'); return }
    try {
      const res = await runApi.lock(runId, value)
      run.value = res.data.data
      ElMessage.success('批次已锁定')
    } catch (err: any) {
      ElMessage.error(err.response?.data?.message || '锁定失败')
    }
  }).catch(() => {})
}

function handleUnlock() {
  ElMessageBox.prompt('解锁后可以修改数据，请输入解锁原因', '解锁批次', {
    confirmButtonText: '解锁',
    cancelButtonText: '取消',
    inputPlaceholder: '解锁原因',
  }).then(async ({ value }) => {
    if (!value) { ElMessage.warning('请填写解锁原因'); return }
    try {
      const res = await runApi.unlock(runId, value)
      run.value = res.data.data
      ElMessage.success('批次已解锁')
    } catch (err: any) {
      ElMessage.error(err.response?.data?.message || '解锁失败')
    }
  }).catch(() => {})
}

// 摘要数据
const summaryData = computed(() => {
  if (!run.value) return { empCount: '--', blockCount: '--', warnCount: '--', totalSalary: '--' }
  const empCount = calculationResults.value.length || '--'
  const totalSalary = calculationResults.value.length > 0
    ? formatMoney(calculationResults.value.reduce((s: number, r: any) => s + parseFloat(r.net_salary || '0'), 0))
    : '--'
  return {
    empCount,
    blockCount: run.value.block_count ?? 0,
    warnCount: run.value.warn_count ?? 0,
    totalSalary,
  }
})
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <!-- 面包屑 -->
      <div class="page-breadcrumb" style="padding-top:24px">
        <a href="javascript:;" @click="router.push('/')">工资核算任务</a>
        <span class="sep">/</span>
        <span>{{ run?.name || '任务详情' }}</span>
      </div>

      <!-- 页面头部 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap">
            <h1 class="page-title" style="font-size:22px">{{ run?.name || '任务详情' }}</h1>
            <el-tag v-if="run" :type="statusTag(run.status)" effect="plain" size="small">
              {{ statusLabel(run.status) }}
            </el-tag>
            <span v-if="run" class="text-tertiary" style="font-size:13px">
              {{ formatMonth(run.payroll_month) }}
            </span>
            <span v-if="run && hasResults" class="text-tertiary" style="font-size:13px">
              v{{ run.current_calc_version }}
            </span>
          </div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap">
          <!-- 根据状态展示操作 -->
          <template v-if="!isExported">
            <el-button v-if="run?.status === 'CREATED'" type="primary" @click="goToStep(steps[1], 1)">
              <el-icon><Upload /></el-icon>开始导入
            </el-button>
            <el-button v-if="canGoToCheck" type="primary" @click="goToStep(steps[3], 3)">
              <el-icon><Select /></el-icon>数据检查
            </el-button>
            <el-button v-if="run?.status === 'CHECK_FAILED'" type="danger" @click="goToStep(steps[4], 4)">
              <el-icon><WarningFilled /></el-icon>异常处理
            </el-button>
            <el-button v-if="canGoToCalculate" type="primary" @click="goToStep(steps[5], 5)">
              <el-icon><Coin /></el-icon>工资计算
            </el-button>
            <el-button v-if="hasResults" @click="goToStep(steps[6], 6)">
              <el-icon><Reading /></el-icon>工资解释
            </el-button>
            <el-button v-if="hasResults" @click="goToStep(steps[7], 7)">
              <el-icon><Download /></el-icon>导出
            </el-button>
            <el-button text @click="loadRun">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </template>
          <!-- 已导出/已确认/已锁定状态 -->
          <template v-else>
            <el-button v-if="run?.status === 'CALCULATED'" type="success" @click="handleConfirm">
              <el-icon><CircleCheck /></el-icon>确认数据
            </el-button>
            <el-button v-if="run?.status === 'CONFIRMED'" @click="handleLock">
              <el-icon><Lock /></el-icon>锁定批次
            </el-button>
            <el-button v-if="run?.status === 'LOCKED'" @click="handleUnlock">
              <el-icon><Unlock /></el-icon>解锁批次
            </el-button>
            <el-button type="primary" @click="goToStep(steps[8], 8)"><el-icon><Download /></el-icon>下载工资表</el-button>
            <el-button @click="goToStep(steps[7], 7)"><el-icon><Reading /></el-icon>查看工资解释</el-button>
          </template>
        </div>
      </div>

      <div v-loading="loading">
        <!-- 步骤条 -->
        <div class="content-card" style="padding:16px 20px">
          <div class="step-bar">
            <div
              v-for="(step, i) in steps"
              :key="i"
              class="step-item"
              :class="{
                'step-done': stepStatuses[i] === 'success',
                'step-active': stepStatuses[i] === 'process',
                'step-error': stepStatuses[i] === 'danger',
                'step-wait': stepStatuses[i] === 'wait',
                'step-clickable': stepStatuses[i] === 'success' || stepStatuses[i] === 'process',
              }"
              @click="goToStep(step, i)"
            >
              <div class="step-icon">
                <el-icon v-if="stepStatuses[i] === 'success'" :size="14"><Check /></el-icon>
                <el-icon v-else-if="stepStatuses[i] === 'danger'" :size="14"><Close /></el-icon>
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div class="step-label">{{ step.title }}</div>
              <div v-if="i < steps.length - 1" class="step-line" :class="{ 'step-line-done': stepStatuses[i] === 'success' }" />
            </div>
          </div>
          <p style="font-size:13px; color:var(--text-secondary); margin-top:10px; text-align:center">
            {{ currentStepDesc }}
          </p>
        </div>

        <!-- 摘要指标 -->
        <div class="stat-cards" style="margin-bottom:16px">
          <div class="stat-card" style="height:80px">
            <div class="stat-card-icon blue">
              <el-icon :size="18"><User /></el-icon>
            </div>
            <div class="stat-card-body">
              <div class="stat-card-value">{{ summaryData.empCount }}</div>
              <div class="stat-card-label">员工人数</div>
            </div>
          </div>
          <div class="stat-card" style="height:80px">
            <div class="stat-card-icon orange">
              <el-icon :size="18"><WarningFilled /></el-icon>
            </div>
            <div class="stat-card-body">
              <div class="stat-card-value">{{ summaryData.blockCount }}</div>
              <div class="stat-card-label">阻断异常</div>
            </div>
          </div>
          <div class="stat-card" style="height:80px">
            <div class="stat-card-icon orange">
              <el-icon :size="18"><Warning /></el-icon>
            </div>
            <div class="stat-card-body">
              <div class="stat-card-value">{{ summaryData.warnCount }}</div>
              <div class="stat-card-label">警告数量</div>
            </div>
          </div>
          <div class="stat-card" style="height:80px">
            <div class="stat-card-icon green">
              <el-icon :size="18"><Money /></el-icon>
            </div>
            <div class="stat-card-body">
              <div class="stat-card-value" style="font-size:18px">{{ summaryData.totalSalary }}</div>
              <div class="stat-card-label">实发工资总额</div>
            </div>
          </div>
        </div>

        <!-- 任务信息 -->
        <div class="content-card" v-if="run">
          <div class="content-card-header">
            <div class="content-card-title">基本信息</div>
          </div>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">工资月份</span>
              <span class="info-value">{{ formatMonth(run.payroll_month) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">当前状态</span>
              <span class="info-value">
                <el-tag :type="statusTag(run.status)" size="small" effect="plain">{{ statusLabel(run.status) }}</el-tag>
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">计算版本</span>
              <span class="info-value">{{ (run.current_calc_version ?? 0) > 0 ? `v${run.current_calc_version}` : '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建人</span>
              <span class="info-value">{{ run.created_by || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatDate(run.created_at) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">最后更新</span>
              <span class="info-value">{{ formatDate(run.updated_at) }}</span>
            </div>
            <div v-if="run.remark" class="info-item" style="grid-column:span 2">
              <span class="info-label">备注</span>
              <span class="info-value">{{ run.remark }}</span>
            </div>
          </div>
        </div>

        <!-- 下一步操作面板 -->
        <TaskQuickActions :run-id="runId" :run="run" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 自定义步骤条 */
.step-bar {
  display: flex;
  align-items: flex-start;
  gap: 0;
  padding: 4px 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
  min-width: 0;
}

.step-item.step-clickable {
  cursor: pointer;
}

.step-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.step-done .step-icon {
  background: var(--success);
  color: #fff;
}

.step-active .step-icon {
  background: var(--primary);
  color: #fff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.step-error .step-icon {
  background: var(--danger);
  color: #fff;
}

.step-wait .step-icon {
  background: #F3F4F6;
  color: var(--text-tertiary);
}

.step-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
  text-align: center;
  white-space: nowrap;
}

.step-done .step-label {
  color: var(--success);
  font-weight: 500;
}

.step-active .step-label {
  color: var(--primary);
  font-weight: 500;
}

.step-line {
  position: absolute;
  top: 14px;
  left: calc(50% + 16px);
  right: calc(-50% + 16px);
  height: 2px;
  background: #E5E7EB;
  z-index: 0;
}

.step-line-done {
  background: var(--success);
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.info-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  align-items: center;
}

.info-item:last-child,
.info-item:nth-last-child(2):nth-child(odd) {
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 70px;
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
}
</style>
