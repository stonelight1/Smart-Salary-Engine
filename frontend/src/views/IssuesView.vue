<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkApi } from '@/api'
import type { IssueItem } from '@/types'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const issues = ref<IssueItem[]>([])
const loading = ref(false)
const filterLevel = ref('')
const filterStatus = ref('')

// 处理对话框
const dialogVisible = ref(false)
const currentIssue = ref<IssueItem | null>(null)
const resolveAction = ref('')
const resolveValue = ref('')
const resolveReason = ref('')
const resolving = ref(false)

const isMissingField = computed(() => {
  return currentIssue.value?.issue_code === 'FIELD_OPTIONAL_MISSING'
})

const isRequiredMissing = computed(() => {
  return currentIssue.value?.issue_code === 'FIELD_REQUIRED_MISSING'
})

const MISSING_OPTIONS = [
  { value: 'FILL_ZERO', label: '按 0 元计算', desc: '缺少的数据按 0 处理' },
  { value: 'FILL_ONE', label: '按 1 计算', desc: '绩效系数等按 1 计算（仅系数适用）' },
  { value: 'FILL_VALUE', label: '填写具体值', desc: '手动录入实际金额或数值' },
  { value: 'IGNORE_ISSUE', label: '暂不处理', desc: '保留异常，后续再处理' },
]

const REQUIRED_OPTIONS = [
  { value: 'FILL_VALUE', label: '补录值', desc: '手动填写缺失的必填字段' },
  { value: 'IGNORE_ISSUE', label: '忽略', desc: '确认跳过此项检查' },
]

const genericOptions = [
  { value: 'CONFIRM', label: '确认', desc: '确认当前数据正确' },
  { value: 'IGNORE_ISSUE', label: '忽略', desc: '忽略此异常' },
]

const displayOptions = computed(() => {
  if (isMissingField.value) return MISSING_OPTIONS
  if (isRequiredMissing.value) return REQUIRED_OPTIONS
  return genericOptions
})

const showValueInput = computed(() => {
  return resolveAction.value === 'FILL_VALUE'
})

const levelTag = (lvl: string) => {
  const m: Record<string, string> = { BLOCK: 'danger', WARN: 'warning', INFO: 'info' }
  return m[lvl] || 'info'
}

onMounted(() => fetchIssues())

async function fetchIssues() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (filterLevel.value) params.level = filterLevel.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await checkApi.getIssues(runId, params)
    issues.value = res.data.data.items || []
  } catch {
    ElMessage.error('获取异常列表失败')
  } finally {
    loading.value = false
  }
}

function openResolveDialog(issue: IssueItem) {
  currentIssue.value = issue
  resolveAction.value = ''
  resolveValue.value = ''
  resolveReason.value = ''
  dialogVisible.value = true
}

async function handleResolve() {
  if (!currentIssue.value || !resolveAction.value) return
  resolving.value = true
  try {
    await checkApi.resolveIssue(currentIssue.value.issue_id, {
      action: resolveAction.value,
      value: resolveValue.value || undefined,
      reason: resolveReason.value || '人工处理',
    })
    ElMessage.success('异常已处理')
    dialogVisible.value = false
    fetchIssues()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '处理失败')
  } finally {
    resolving.value = false
  }
}

function recheck() {
  checkApi.run(runId).then(() => {
    ElMessage.success('重新检查完成')
    fetchIssues()
  }).catch((err: any) => {
    ElMessage.error(err.response?.data?.message || '检查失败')
  })
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
        <span>异常中心</span>
      </div>

      <div class="page-header" style="padding-top:12px; display:flex; align-items:flex-start; justify-content:space-between">
        <div class="page-header-left">
          <h1 class="page-title">异常中心</h1>
          <p class="page-subtitle">查看和处理数据检查中发现的异常</p>
        </div>
        <el-button size="default" @click="recheck"><el-icon><Refresh /></el-icon>重新检查</el-button>
      </div>

      <div class="content-card">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px">
          <el-select v-model="filterLevel" placeholder="异常等级" clearable style="width:130px" @change="fetchIssues">
            <el-option label="阻断" value="BLOCK" />
            <el-option label="警告" value="WARN" />
            <el-option label="提示" value="INFO" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="状态" clearable style="width:130px" @change="fetchIssues">
            <el-option label="待处理" value="OPEN" />
            <el-option label="已解决" value="RESOLVED" />
            <el-option label="已忽略" value="IGNORED" />
          </el-select>
          <span style="color:var(--text-tertiary); font-size:13px">
            共 {{ issues.length }} 条
          </span>
        </div>

        <el-table :data="issues" v-loading="loading" stripe>
          <el-table-column label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="levelTag(row.level)" size="small">
                {{ row.level === 'BLOCK' ? '阻断' : row.level === 'WARN' ? '警告' : '提示' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="employee_name" label="员工" width="120" />
          <el-table-column prop="field_code" label="字段" width="120" />
          <el-table-column prop="message" label="异常说明" min-width="300" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'OPEN' ? 'danger' : row.status === 'RESOLVED' ? 'success' : 'info'" size="small">
                {{ row.status === 'OPEN' ? '待处理' : row.status === 'RESOLVED' ? '已解决' : '已忽略' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.status === 'OPEN'" size="small" @click="openResolveDialog(row)"><el-icon><Tools /></el-icon>处理</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && issues.length === 0" description="暂无异常" />
      </div>
    </div>

    <!-- 处理对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="'处理异常'"
      width="480px"
      :close-on-click-modal="false"
    >
      <div v-if="currentIssue" style="margin-bottom:16px">
        <div style="display:flex; gap:8px; align-items:center; margin-bottom:8px">
          <el-tag :type="levelTag(currentIssue.level)" size="small">
            {{ currentIssue.level === 'BLOCK' ? '阻断' : currentIssue.level === 'WARN' ? '警告' : '提示' }}
          </el-tag>
          <span style="font-weight:500; color:var(--text-primary)">{{ currentIssue.employee_name }}</span>
        </div>
        <p style="font-size:14px; color:var(--text-secondary); margin:0">
          {{ currentIssue.message }}
        </p>
      </div>

      <!-- 处理选项 -->
      <div style="margin-bottom:16px">
        <p style="font-size:13px; color:var(--text-secondary); font-weight:500; margin-bottom:8px">选择处理方式</p>
        <div class="resolve-options">
          <div
            v-for="opt in displayOptions"
            :key="opt.value"
            class="resolve-option"
            :class="{ 'option-selected': resolveAction === opt.value }"
            @click="resolveAction = opt.value; if (opt.value !== 'FILL_VALUE') resolveValue = ''"
          >
            <div class="option-radio">
              <span :class="['radio-dot', { 'radio-active': resolveAction === opt.value }]" />
            </div>
            <div class="option-content">
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 填写值 -->
      <el-form v-if="showValueInput" label-position="top" style="margin-bottom:16px">
        <el-form-item label="填写值">
          <el-input v-model="resolveValue" placeholder="输入金额或数值" />
        </el-form-item>
      </el-form>

      <!-- 备注 -->
      <el-form label-position="top">
        <el-form-item label="处理说明（可选）">
          <el-input v-model="resolveReason" placeholder="可不填" maxlength="200" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false"><el-icon><Close /></el-icon>取消</el-button>
        <el-button type="primary" :loading="resolving" :disabled="!resolveAction" @click="handleResolve">
          <el-icon><CircleCheck /></el-icon>确认处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.resolve-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resolve-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.resolve-option:hover {
  border-color: #D1D5DB;
  background: #FAFBFC;
}

.resolve-option.option-selected {
  border-color: var(--primary);
  background: var(--primary-light);
}

.option-radio {
  flex-shrink: 0;
}

.radio-dot {
  display: block;
  width: 16px;
  height: 16px;
  border: 2px solid #D1D5DB;
  border-radius: 50%;
  transition: border-color 0.15s;
}

.radio-dot.radio-active {
  border-color: var(--primary);
  background: var(--primary);
  box-shadow: inset 0 0 0 3px #fff;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.option-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.option-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
