<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adjustmentApi, employeeApi } from '@/api'
import { formatDate, formatMoney } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const adjustments = ref<any[]>([])
const employees = ref<any[]>([])
const loading = ref(false)
const employeeFilter = ref('')

// 新建对话框
const dialogVisible = ref(false)
const creating = ref(false)
const newAdjustment = ref({
  employee_record_id: '',
  employee_name: '',
  field_code: '',
  adjustment_type: '',
  amount: '',
  reason: '',
})

const ADJUSTMENT_TYPES = [
  { value: 'overtime_pay', label: '加班费', field: 'overtime_pay', category: '应发' },
  { value: 'meal_allowance', label: '餐补', field: 'meal_allowance', category: '应发' },
  { value: 'traffic_allowance', label: '交通补贴', field: 'traffic_allowance', category: '应发' },
  { value: 'fuel_allowance', label: '油补', field: 'other_income', category: '应发' },
  { value: 'equipment_subsidy', label: '设备补贴', field: 'other_income', category: '应发' },
  { value: 'recruitment_bonus', label: '招聘奖金', field: 'other_income', category: '应发' },
  { value: 'management_bonus', label: '管理奖金', field: 'other_income', category: '应发' },
  { value: 'back_pay', label: '补发工资', field: 'other_income', category: '应发' },
  { value: 'other_income', label: '其他应发', field: 'other_income', category: '应发' },
  { value: 'other_deduction', label: '其他扣款', field: 'other_deduction', category: '扣款' },
  { value: 'social_supplement', label: '社保补扣', field: 'social_security_personal', category: '扣款' },
  { value: 'fund_supplement', label: '公积金补扣', field: 'housing_fund_personal', category: '扣款' },
]

// 按类别分组
const incomeTypes = computed(() => ADJUSTMENT_TYPES.filter((t) => t.category === '应发'))
const deductionTypes = computed(() => ADJUSTMENT_TYPES.filter((t) => t.category === '扣款'))

const filteredAdjustments = computed(() => {
  if (!employeeFilter.value) return adjustments.value
  return adjustments.value.filter((a) => a.employee_record_id === employeeFilter.value)
})

// 总计
const totalAmount = computed(() => {
  const total = filteredAdjustments.value
    .filter((a) => a.status === 'ACTIVE')
    .reduce((s, a) => s + parseFloat(a.amount || '0'), 0)
  return formatMoney(total)
})

onMounted(async () => {
  await Promise.all([fetchAdjustments(), fetchEmployees()])
})

async function fetchAdjustments() {
  loading.value = true
  try {
    const res = await adjustmentApi.list(runId, employeeFilter.value || undefined)
    adjustments.value = res.data.data.items || []
  } catch {
    ElMessage.error('获取调整项失败')
  } finally {
    loading.value = false
  }
}

async function fetchEmployees() {
  try {
    const res = await employeeApi.list(runId)
    employees.value = res.data.data.items || []
  } catch {
    // ignore
  }
}

function openCreateDialog() {
  newAdjustment.value = {
    employee_record_id: '',
    employee_name: '',
    field_code: '',
    adjustment_type: '',
    amount: '',
    reason: '',
  }
  dialogVisible.value = true
}

async function handleCreate() {
  const na = newAdjustment.value
  if (!na.employee_record_id) { ElMessage.warning('请选择员工'); return }
  if (!na.adjustment_type) { ElMessage.warning('请选择调整类型'); return }
  if (!na.amount || parseFloat(na.amount) === 0) { ElMessage.warning('请输入调整金额'); return }
  if (!na.reason) { ElMessage.warning('请填写调整原因'); return }

  const typeInfo = ADJUSTMENT_TYPES.find((t) => t.value === na.adjustment_type)
  if (!typeInfo) return

  creating.value = true
  try {
    await adjustmentApi.create(runId, {
      employee_record_id: na.employee_record_id,
      field_code: typeInfo.field,
      adjustment_type: na.adjustment_type,
      amount: na.amount,
      reason: na.reason,
    })
    ElMessage.success('调整项已添加')
    dialogVisible.value = false
    await fetchAdjustments()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

function handleRevert(adj: any) {
  ElMessageBox.confirm(
    `确认撤销对「${adj.employee_name}」的${getTypeLabel(adj.adjustment_type)}调整（${formatMoney(adj.amount)}元）？`,
    '撤销确认',
    {
      confirmButtonText: '确认撤销',
      cancelButtonText: '取消',
      type: 'warning',
    },
  ).then(async () => {
    try {
      await adjustmentApi.revert(adj.id)
      ElMessage.success('调整项已撤销')
      await fetchAdjustments()
    } catch (err: any) {
      ElMessage.error(err.response?.data?.message || '撤销失败')
    }
  }).catch(() => {})
}

function getTypeLabel(type: string): string {
  return ADJUSTMENT_TYPES.find((t) => t.value === type)?.label || type
}

function getTypeCategory(type: string): string {
  return ADJUSTMENT_TYPES.find((t) => t.value === type)?.category || ''
}

function handleFilterChange() {
  fetchAdjustments()
}
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <!-- 面包屑 -->
      <div class="page-breadcrumb" style="padding-top:24px">
        <a href="javascript:;" @click="router.push('/')">工资核算任务</a>
        <span class="sep">/</span>
        <a href="javascript:;" @click="router.push(`/runs/${runId}`)">任务详情</a>
        <span class="sep">/</span>
        <span>调整中心</span>
      </div>

      <!-- 页面标题 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">调整中心</h1>
          <p class="page-subtitle">管理人工调整项 — 原始数据 + 调整项 = 计算使用值</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon style="margin-right:4px"><Plus /></el-icon>
          新增调整项
        </el-button>
      </div>

      <!-- 筛选 -->
      <div class="filter-bar">
        <div class="filter-item">
          <label>员工</label>
          <el-select v-model="employeeFilter" placeholder="全部员工" clearable style="width:200px" @change="handleFilterChange">
            <el-option v-for="e in employees" :key="e.employee_ref_id" :label="e.employee_name" :value="e.employee_ref_id" />
          </el-select>
        </div>
        <div class="filter-actions">
          <span style="font-size:13px; color:var(--text-tertiary)">
            调整合计：<strong style="color:var(--text-primary)">{{ totalAmount }}</strong> 元
          </span>
        </div>
      </div>

      <!-- 调整项表格 -->
      <div class="content-card" style="padding:0; overflow:hidden">
        <el-table :data="filteredAdjustments" v-loading="loading" stripe style="width:100%">
          <el-table-column prop="employee_name" label="员工" width="120" />
          <el-table-column label="调整类型" width="130">
            <template #default="{ row }">
              <el-tag size="small" :type="getTypeCategory(row.adjustment_type) === '扣款' ? 'danger' : 'success'" effect="plain">
                {{ getTypeLabel(row.adjustment_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="130" align="right">
            <template #default="{ row }">
              <span :style="{ color: getTypeCategory(row.adjustment_type) === '扣款' ? 'var(--danger)' : 'var(--success)', fontWeight:600 }">
                {{ getTypeCategory(row.adjustment_type) === '扣款' ? '-' : '+' }}{{ formatMoney(row.amount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="200" />
          <el-table-column prop="created_by" label="操作人" width="100" />
          <el-table-column label="操作时间" width="150">
            <template #default="{ row }">
              <span class="text-tertiary" style="font-size:13px">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">
                {{ row.status === 'ACTIVE' ? '生效' : '已撤销' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'ACTIVE'" size="small" text @click="handleRevert(row)"><el-icon><Close /></el-icon>撤销</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && adjustments.length === 0" description="暂无调整项">
          <template #image>
            <el-icon :size="48" style="color:#D1D5DB"><EditPen /></el-icon>
          </template>
          <el-button type="primary" @click="openCreateDialog">新增调整项</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 新增调整项对话框 -->
    <el-dialog v-model="dialogVisible" title="新增调整项" width="520px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="员工" required>
          <el-select v-model="newAdjustment.employee_record_id" filterable placeholder="搜索并选择员工" style="width:100%">
            <el-option v-for="e in employees" :key="e.employee_ref_id" :label="e.employee_name" :value="e.employee_ref_id" />
          </el-select>
        </el-form-item>

        <el-form-item label="调整类型" required>
          <div style="display:flex; flex-wrap:wrap; gap:6px">
            <div style="width:100%; font-size:13px; color:var(--text-secondary); margin-bottom:4px">应发类</div>
            <el-tag
              v-for="t in incomeTypes"
              :key="t.value"
              :type="newAdjustment.adjustment_type === t.value ? 'success' : 'info'"
              effect="plain"
              style="cursor:pointer"
              @click="newAdjustment.adjustment_type = t.value; newAdjustment.field_code = t.field"
            >
              {{ t.label }}
            </el-tag>
            <div style="width:100%; font-size:13px; color:var(--text-secondary); margin:8px 0 4px">扣款类</div>
            <el-tag
              v-for="t in deductionTypes"
              :key="t.value"
              :type="newAdjustment.adjustment_type === t.value ? 'danger' : 'info'"
              effect="plain"
              style="cursor:pointer"
              @click="newAdjustment.adjustment_type = t.value; newAdjustment.field_code = t.field"
            >
              {{ t.label }}
            </el-tag>
          </div>
        </el-form-item>

        <el-form-item label="金额（元）" required>
          <el-input-number v-model="newAdjustment.amount" :min="0" :precision="2" :step="100" style="width:100%" placeholder="输入调整金额" controls-position="right" />
        </el-form-item>

        <el-form-item label="调整原因" required>
          <el-input v-model="newAdjustment.reason" type="textarea" :rows="2" placeholder="例如：补发3月绩效差额 300 元" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false"><el-icon><Close /></el-icon>取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          <el-icon><CircleCheck /></el-icon>确认添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 12px 20px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-item label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.filter-actions {
  margin-left: auto;
  font-size: 13px;
}
</style>
