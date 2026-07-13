<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runApi, importApi } from '@/api'
import { formatDate, formatMonth } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const run = ref<any>(null)
const loading = ref(false)
const perfUploading = ref(false)
const leaveUploading = ref(false)
const generatingDraft = ref(false)
const confirmingFinal = ref(false)
const perfStatus = ref<any>(null)
const leaveStatus = ref<any>(null)
const employees = ref<any[]>([])

onMounted(() => loadRun())

async function loadRun() {
  loading.value = true
  try {
    const res = await runApi.get(runId)
    run.value = res.data.data
    await loadEmployees()
    await loadPerfStatus()
    await loadLeaveStatus()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '获取任务失败')
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  try {
    const res = await importApi.getFiles(runId)
    // Get employee list from run details
    const empRes = await runApi.get(runId)
    // employees would normally come from a dedicated endpoint
  } catch {}
}

async function loadPerfStatus() {
  try {
    const res = await fetch(`/api/v2/runs/${runId}/performance/status`)
    if (res.ok) {
      const data = await res.json()
      perfStatus.value = data.data
    }
  } catch {}
}

async function loadLeaveStatus() {
  try {
    const res = await fetch(`/api/v2/runs/${runId}/leave/status`)
    if (res.ok) {
      const data = await res.json()
      leaveStatus.value = data.data
    }
  } catch {}
}

async function handleGenerateDraft() {
  try {
    await ElMessageBox.confirm(
      '将基于上个月最终版生成本月工资草稿，已有数据将被覆盖。是否继续？',
      '生成本月草稿',
      { confirmButtonText: '确认生成', cancelButtonText: '取消', type: 'info' },
    )
  } catch { return }

  generatingDraft.value = true
  try {
    
    const res = await fetch(`/api/v2/runs/${runId}/generate-draft`, {
      method: 'POST',
      headers: {},
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success(`草稿生成成功，继承 ${data.data.employee_count} 名员工`)
      await loadRun()
    } else {
      ElMessage.error(data.message || '生成失败')
    }
  } catch (err: any) {
    ElMessage.error(err.message || '生成失败')
  } finally {
    generatingDraft.value = false
  }
}

async function handleImportPerf() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    perfUploading.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      
      const res = await fetch(`/api/v2/runs/${runId}/performance/import`, {
        method: 'POST',
        headers: {},
        body: form,
      })
      const data = await res.json()
      if (data.success) {
        ElMessage.success(`绩效导入成功：${data.data.matched_count} 条匹配`)
        if (data.data.unmatched_count > 0) {
          ElMessage.warning(`${data.data.unmatched_count} 名员工未匹配`)
        }
        await loadPerfStatus()
      } else {
        ElMessage.error(data.message || '导入失败')
      }
    } catch (err: any) {
      ElMessage.error(err.message || '导入失败')
    } finally {
      perfUploading.value = false
    }
  }
  input.click()
}

async function handleImportLeave() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    leaveUploading.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      
      const res = await fetch(`/api/v2/runs/${runId}/leave/import`, {
        method: 'POST',
        headers: {},
        body: form,
      })
      const data = await res.json()
      if (data.success) {
        ElMessage.success(`请假导入成功：${data.data.matched_count} 条记录`)
        if (data.data.unmatched_count > 0) {
          ElMessage.warning(`${data.data.unmatched_count} 条记录未匹配`)
        }
        await loadLeaveStatus()
      } else {
        ElMessage.error(data.message || '导入失败')
      }
    } catch (err: any) {
      ElMessage.error(err.message || '导入失败')
    } finally {
      leaveUploading.value = false
    }
  }
  input.click()
}

async function handleConfirmFinal() {
  try {
    await ElMessageBox.confirm(
      '确认最终版后，本月工资数据将锁定，无法直接修改。如需修改需退回草稿。是否确认？',
      '确认最终版',
      { confirmButtonText: '确认最终版', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }

  confirmingFinal.value = true
  try {
    
    const res = await fetch(`/api/v2/runs/${runId}/confirm-final`, {
      method: 'POST',
      headers: {},
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('已标记为最终版')
      await loadRun()
    } else {
      ElMessage.error(data.message || '确认失败')
    }
  } catch (err: any) {
    ElMessage.error(err.message || '确认失败')
  } finally {
    confirmingFinal.value = false
  }
}

const isDraft = computed(() => run.value?.run_version === 'DRAFT' || !run.value?.run_version)
</script>

<template>
  <div class="page-layout" v-loading="loading">
    <div class="page-container">
      <!-- 面包屑 -->
      <div class="page-breadcrumb" style="padding-top: 24px">
        <a href="javascript:;" @click="router.push('/')">工资核算任务</a>
        <span class="sep">/</span>
        <span>{{ run?.name || '工资核算' }}</span>
      </div>

      <!-- 标题区 -->
      <div class="page-header" style="padding-top: 12px">
        <div>
          <h1 class="page-title">{{ run?.name || '工资核算' }}</h1>
          <p class="page-subtitle">
            {{ formatMonth(run?.payroll_month) }}
            <template v-if="run?.reference_run_id">
              · 参考版本：{{ run?.reference_run_id?.slice(0, 12) }}
            </template>
            · 当前版本：<strong>{{ run?.run_version || 'DRAFT' }}</strong>
            · 状态：<strong>{{ run?.status }}</strong>
          </p>
        </div>
      </div>

      <!-- 操作流 -->
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">工资核算流程</div>
        </div>
        <div class="v2-flow">
          <!-- Step 1: 人员异动 -->
          <div class="flow-step">
            <div class="step-icon step-ready">1</div>
            <div class="step-body">
              <div class="step-title">人员异动</div>
              <div class="step-desc">调整本月员工名单（新增、离职、调岗、调薪）</div>
              <div class="step-actions">
                <el-button size="small" type="primary" @click="handleGenerateDraft" :loading="generatingDraft">
                  生成本月草稿
                </el-button>
                <el-button size="small" @click="router.push(`/runs/${runId}/import`)">管理员工数据</el-button>
              </div>
            </div>
          </div>

          <!-- Step 2: 绩效导入 -->
          <div class="flow-step">
            <div class="step-icon" :class="perfStatus?.imported_count > 0 ? 'step-done' : 'step-pending'">2</div>
            <div class="step-body">
              <div class="step-title">绩效导入</div>
              <div class="step-desc">导入本月绩效得分 Excel</div>
              <div v-if="perfStatus" class="step-stats">
                <span class="stat-item">已导入：{{ perfStatus.imported_count }} 人</span>
                <span class="stat-item">默认满分：{{ perfStatus.default_score_count }} 人</span>
                <span v-if="perfStatus.unmatched_count" class="stat-item stat-warn">
                  未匹配：{{ perfStatus.unmatched_count }} 人
                </span>
              </div>
              <div class="step-actions">
                <el-button size="small" :loading="perfUploading" @click="handleImportPerf">
                  导入绩效
                </el-button>
              </div>
            </div>
          </div>

          <!-- Step 3: 请假导入 -->
          <div class="flow-step">
            <div class="step-icon" :class="leaveStatus?.total_leave_days > 0 ? 'step-done' : 'step-pending'">3</div>
            <div class="step-body">
              <div class="step-title">请假导入</div>
              <div class="step-desc">导入企业微信请假 Excel</div>
              <div v-if="leaveStatus" class="step-stats">
                <span class="stat-item">有请假员工：{{ leaveStatus.employee_with_leave_count }} 人</span>
                <span class="stat-item">请假总天数：{{ leaveStatus.total_leave_days }} 天</span>
                <span v-if="leaveStatus.unmatched_count" class="stat-item stat-warn">
                  未匹配：{{ leaveStatus.unmatched_count }}
                </span>
              </div>
              <div class="step-actions">
                <el-button size="small" :loading="leaveUploading" @click="handleImportLeave">
                  导入请假
                </el-button>
              </div>
            </div>
          </div>

          <!-- Step 4: 工资计算 -->
          <div class="flow-step">
            <div class="step-icon" :class="run?.current_calc_version > 0 ? 'step-done' : 'step-pending'">4</div>
            <div class="step-body">
              <div class="step-title">工资计算</div>
              <div class="step-desc">基于新公式执行工资计算</div>
              <div v-if="run?.current_calc_version > 0" class="step-stats">
                <span class="stat-item">当前版本：v{{ run.current_calc_version }}</span>
              </div>
              <div class="step-actions">
                <el-button size="small" @click="router.push(`/runs/${runId}/calculate`)">
                  执行计算
                </el-button>
                <el-button size="small" @click="router.push(`/runs/${runId}/explain`)">
                  查看明细
                </el-button>
              </div>
            </div>
          </div>

          <!-- Step 5: 异常检查 -->
          <div class="flow-step">
            <div class="step-icon step-pending">5</div>
            <div class="step-body">
              <div class="step-title">异常检查</div>
              <div class="step-desc">检查数据完整性和计算一致性</div>
              <div class="step-actions">
                <el-button size="small" @click="router.push(`/runs/${runId}/check`)">
                  开始检查
                </el-button>
              </div>
            </div>
          </div>

          <!-- Step 6: 确认最终版 -->
          <div class="flow-step">
            <div class="step-icon" :class="run?.run_version === 'FINAL' ? 'step-done' : 'step-pending'">6</div>
            <div class="step-body">
              <div class="step-title">确认最终版</div>
              <div class="step-desc">锁定本月工资数据，标记为最终版</div>
              <div v-if="run?.run_version === 'FINAL'" class="step-stats">
                <span class="stat-item stat-ok">已确认最终版</span>
              </div>
              <div class="step-actions">
                <el-button
                  size="small"
                  type="primary"
                  :loading="confirmingFinal"
                  :disabled="run?.status !== 'CONFIRMED'"
                  @click="handleConfirmFinal"
                >
                  确认最终版
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 回到首页 -->
      <div style="text-align: center; padding: 20px 0">
        <el-button @click="router.push('/')">
          返回工作台
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.v2-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-step {
  display: flex;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: border-color 0.15s;
}

.flow-step:hover {
  border-color: #D1D5DB;
}

.step-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-ready {
  background: #2563EB;
  color: #fff;
}

.step-done {
  background: #16A34A;
  color: #fff;
}

.step-pending {
  background: #F3F4F6;
  color: #9CA3AF;
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.step-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.step-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.stat-item {
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-item.stat-warn {
  color: #D97706;
}

.stat-item.stat-ok {
  color: #16A34A;
  font-weight: 500;
}

.step-actions {
  display: flex;
  gap: 8px;
}
</style>
