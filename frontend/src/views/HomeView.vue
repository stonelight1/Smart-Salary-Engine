<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runApi } from '@/api'
import type { RunStatusInfo } from '@/types'
import { getStageIndex } from '@/utils'

import PayrollWorkspaceHeader from '@/components/payroll/PayrollWorkspaceHeader.vue'
import PayrollMetrics from '@/components/payroll/PayrollMetrics.vue'
import PayrollStageNavigator from '@/components/payroll/PayrollStageNavigator.vue'
import PayrollTaskTable from '@/components/payroll/PayrollTaskTable.vue'

const router = useRouter()

/* ---- 数据状态 ---- */
const runs = ref<RunStatusInfo[]>([])
const loading = ref(false)
const total = ref(0)
const operating = ref(false)

const keyword = ref('')
const filterMonth = ref('')
const filterStatus = ref('')
const includeArchived = ref(false)

const page = ref(1)
const pageSize = ref(20)

const activeFilter = ref<string | null>(null)
const activeStage = ref(-1)

onMounted(() => fetchRuns())

/* ---- API ---- */
async function fetchRuns() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (keyword.value) params.keyword = keyword.value
    if (includeArchived.value) params.include_archived = true
    const res = await runApi.list(params)
    runs.value = res.data.data.items || []
    total.value = res.data.data.total || 0
  } catch {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

/* ---- 派生统计 ---- */

/** 概览统计（基于当前 API 返回页） */
const stats = computed(() => {
  const processing = runs.value.filter((r) =>
    ['CREATED', 'IMPORTING', 'IMPORTED', 'CHECKING', 'CHECK_FAILED', 'CHECK_PASSED', 'CALCULATING', 'CALCULATED'].includes(r.status),
  )
  const abnormal = runs.value.filter((r) => r.status === 'CHECK_FAILED' || r.status === 'FAILED')
  const completed = runs.value.filter((r) => r.status === 'EXPORTED' || r.status === 'LOCKED')
  return {
    processing: processing.length,
    abnormal: abnormal.length,
    completed: completed.length,
  }
})

/** 流程阶段任务数 */
const processCounts = computed(() => {
  const counts = [0, 0, 0, 0, 0, 0]
  for (const r of runs.value) {
    const idx = getStageIndex(r.status)
    if (idx >= 0 && idx < counts.length) counts[idx]++
  }
  return counts
})

/** 阻断/警告统计 */
const alertInfo = computed(() => {
  let blockTasks = 0
  let warnTasks = 0
  for (const r of runs.value) {
    if ((r.block_count ?? 0) > 0) blockTasks++
    if ((r.warn_count ?? 0) > 0) warnTasks++
  }
  return { blockTasks, warnTasks }
})

/** 客户侧筛选后的任务列表 */
const displayRuns = computed(() => {
  let list = runs.value
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter((r) => r.name.toLowerCase().includes(kw))
  }
  if (filterMonth.value) list = list.filter((r) => r.payroll_month === filterMonth.value)
  if (filterStatus.value) list = list.filter((r) => r.status === filterStatus.value)
  if (activeStage.value >= 0) list = list.filter((r) => getStageIndex(r.status) === activeStage.value)
  if (activeFilter.value === 'abnormal') {
    list = list.filter((r) => r.status === 'CHECK_FAILED' || r.status === 'FAILED')
  }
  if (activeFilter.value === 'processing') {
    list = list.filter((r) =>
      ['CREATED', 'IMPORTING', 'IMPORTED', 'CHECKING', 'CHECK_FAILED', 'CHECK_PASSED', 'CALCULATING', 'CALCULATED'].includes(r.status),
    )
  }
  if (activeFilter.value === 'completed') {
    list = list.filter((r) => r.status === 'EXPORTED' || r.status === 'LOCKED')
  }
  return list
})

/* ---- 筛选交互 ---- */

function handleSearch() {
  page.value = 1
  activeFilter.value = null
  activeStage.value = -1
  fetchRuns()
}

function handleReset() {
  keyword.value = ''
  filterMonth.value = ''
  filterStatus.value = ''
  includeArchived.value = false
  activeFilter.value = null
  activeStage.value = -1
  page.value = 1
  fetchRuns()
}

function onMetricFilter(type: string | null) {
  activeFilter.value = type
  activeStage.value = -1
  filterStatus.value = ''
}

function onStageSelect(idx: number) {
  if (activeStage.value === idx) {
    activeStage.value = -1
    activeFilter.value = null
  } else {
    activeStage.value = idx
    activeFilter.value = null
  }
  filterStatus.value = ''
}

function onViewAbnormal() {
  activeFilter.value = 'abnormal'
  activeStage.value = -1
  filterStatus.value = ''
}

function goDetail(run: RunStatusInfo) {
  router.push(`/runs/${run.id}`)
}

/* ---- 任务操作 ---- */

async function handleDelete(run: RunStatusInfo) {
  try {
    await ElMessageBox.confirm(
      `确定删除任务「${run.name}」吗？\n\n删除后，该任务将不再出现在任务列表中，临时数据将无法继续操作。原始上传文件不会被删除。\n\n该操作仅适用于尚未进入正式核算流程的空任务。`,
      '删除核算任务',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning', confirmButtonClass: 'el-button--danger' },
    )
  } catch { return }
  operating.value = true
  try {
    await runApi.delete(run.id)
    ElMessage.success('任务已删除')
    // 删除当前页最后一条时回退页码
    if (displayRuns.value.length === 1 && page.value > 1) page.value--
    await fetchRuns()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '删除失败')
  } finally { operating.value = false }
}

async function handleVoid(run: RunStatusInfo) {
  let reason = ''
  try {
    const { value } = await ElMessageBox.prompt(
      `任务作废后将不能继续计算、审核或导出，但数据和历史操作记录仍会保留。`,
      '作废核算任务',
      {
        confirmButtonText: '确认作废', cancelButtonText: '取消',
        inputPlaceholder: '请填写作废原因（至少5个字符）',
        inputValidator: (v: string) => {
          if (!v || !v.trim()) return '作废原因不能为空'
          if (v.trim().length < 5) return '作废原因至少需要5个字符'
          return true
        },
      },
    )
    reason = value
  } catch { return }
  operating.value = true
  try {
    await runApi.void(run.id, reason.trim())
    ElMessage.success('任务已作废')
    await fetchRuns()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '作废失败')
  } finally { operating.value = false }
}

async function handleArchive(run: RunStatusInfo) {
  try {
    await ElMessageBox.confirm(
      `归档后，该任务将不再显示在默认任务列表中，但数据、计算结果和导出记录仍会保留。`,
      '归档核算任务',
      { confirmButtonText: '确认归档', cancelButtonText: '取消', type: 'info' },
    )
  } catch { return }
  operating.value = true
  try {
    await runApi.archive(run.id)
    ElMessage.success('任务已归档')
    await fetchRuns()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '归档失败')
  } finally { operating.value = false }
}
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <!-- 第一层：标题与主要操作 -->
      <PayrollWorkspaceHeader />

      <!-- 第二层：核心任务概览 -->
      <PayrollMetrics
        :total="total"
        :processing="stats.processing"
        :abnormal="stats.abnormal"
        :completed="stats.completed"
        :active-filter="activeFilter"
        :active-stage="activeStage"
        @filter-change="onMetricFilter"
      />

      <!-- 第三层：核算流程与异常摘要 -->
      <PayrollStageNavigator
        :process-counts="processCounts"
        :active-stage="activeStage"
        :block-tasks="alertInfo.blockTasks"
        :warn-tasks="alertInfo.warnTasks"
        :total="total"
        :runs="runs"
        @stage-select="onStageSelect"
        @view-abnormal="onViewAbnormal"
      />

      <!-- 第四 / 五层：筛选工具栏 + 任务工作列表 -->
      <PayrollTaskTable
        :runs="displayRuns"
        :loading="loading"
        :total="total"
        :page="page"
        :page-size="pageSize"
        :keyword="keyword"
        :filter-month="filterMonth"
        :filter-status="filterStatus"
        :include-archived="includeArchived"
        :operating="operating"
        @update:keyword="keyword = $event"
        @update:filter-month="filterMonth = $event"
        @update:filter-status="filterStatus = $event"
        @update:include-archived="includeArchived = $event"
        @update:page="page = $event"
        @update:page-size="pageSize = $event"
        @search="handleSearch"
        @reset="handleReset"
        @go-detail="goDetail"
        @delete="handleDelete"
        @void="handleVoid"
        @archive="handleArchive"
      />
    </div>
  </div>
</template>
