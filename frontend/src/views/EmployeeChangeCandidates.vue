<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()

const candidates = ref<any[]>([])
const loading = ref(false)
const counts = ref<any>({})
const selected = ref<string[]>([])
const filterType = ref('ALL')

onMounted(() => {
  loadCandidates()
  loadCounts()
})

watch(filterType, () => {
  loadCandidates()
})

async function loadCandidates() {
  loading.value = true
  try {
    
    const params = new URLSearchParams({ status: 'PENDING', page_size: '200' })
    if (filterType.value && filterType.value !== 'ALL') {
      params.set('candidate_type', filterType.value)
    }
    const res = await fetch(`/api/v1/attendance-compare/candidates?${params}`, {
      headers: {},
    })
    const json = await res.json()
    if (json.success) candidates.value = json.data.items || []
  } catch { ElMessage.error('获取失败') }
  finally { loading.value = false }
}

async function loadCounts() {
  try {
    
    const res = await fetch('/api/v1/attendance-compare/counts', {
      headers: {},
    })
    const json = await res.json()
    if (json.success) counts.value = json.data
  } catch {}
}

async function handleAction(cand: any, action: string) {
  let data: any = {}
  if (action === 'CONFIRM_HIRE') {
    try {
      const { value } = await ElMessageBox.prompt(
        `确认入职「${cand.employee_name}」`, '确认入职',
        { confirmButtonText: '确认入职', cancelButtonText: '取消',
          inputValue: cand.hire_date || '',
          inputPlaceholder: '入职日期 (YYYY-MM-DD)', }
      )
      data = { hire_date: value }
    } catch { return }
  } else if (action === 'CONFIRM_TERMINATION') {
    try {
      const { value } = await ElMessageBox.prompt(
        `确认「${cand.employee_name}」离职`, '确认离职',
        { confirmButtonText: '确认离职', cancelButtonText: '取消',
          inputPlaceholder: '离职日期 YYYY-MM-DD', }
      )
      data = { termination_date: value, reason: '确认离职' }
    } catch { return }
  } else if (action === 'KEEP_ACTIVE') {
    try { await ElMessageBox.confirm(`确认「${cand.employee_name}」保持在职？`, '保持在职', { type: 'info' }) }
    catch { return }
  } else if (action === 'IGNORE') {
    try { await ElMessageBox.confirm('确认忽略该记录？', '忽略', { type: 'info' }) }
    catch { return }
  }

  try {
    
    const res = await fetch(`/api/v1/attendance-compare/handle/${cand.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, data }),
    })
    const json = await res.json()
    if (json.success) { ElMessage.success('操作成功'); await loadCandidates(); await loadCounts() }
    else { ElMessage.error(json.message || '操作失败') }
  } catch { ElMessage.error('操作失败') }
}

async function batchConfirm() {
  if (!selected.value.length) return ElMessage.warning('请选择要确认的记录')
  try {
    await ElMessageBox.confirm(`批量确认 ${selected.value.length} 条记录为入职？`, '批量确认', { type: 'info' })
  } catch { return }
  
  const res = await fetch('/api/v1/attendance-compare/batch-confirm', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'CONFIRM_HIRE', candidate_ids: selected.value }),
  })
  const json = await res.json()
  if (json.success) { ElMessage.success(`已确认 ${json.data.confirmed} 条`); selected.value = []; await loadCandidates(); await loadCounts() }
  else { ElMessage.error(json.message || '批量操作失败') }
}

const typeLabel: Record<string, string> = {
  POSSIBLE_HIRE: '疑似入职', POSSIBLE_TERMINATION: '疑似离职',
  DEPARTMENT_CHANGE: '部门变化', POSITION_CHANGE: '岗位变化', INFO_CONFLICT: '信息冲突',
}
const typeTag: Record<string, string> = {
  POSSIBLE_HIRE: 'success', POSSIBLE_TERMINATION: 'danger',
  DEPARTMENT_CHANGE: 'warning', POSITION_CHANGE: 'warning', INFO_CONFLICT: 'danger',
}

const filterOptions = [
  { label: '全部变化', value: 'ALL' },
  { label: '疑似新入职', value: 'POSSIBLE_HIRE' },
  { label: '疑似离职', value: 'POSSIBLE_TERMINATION' },
  { label: '部门变化', value: 'DEPARTMENT_CHANGE' },
  { label: '岗位变化', value: 'POSITION_CHANGE' },
  { label: '信息冲突', value: 'INFO_CONFLICT' },
]
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <div class="page-header">
        <div>
          <h1 class="page-title">本月人员变化</h1>
          <p class="page-subtitle">系统根据考勤数据自动识别的员工变化，请逐一确认</p>
        </div>
        <div>
          <el-button @click="router.push('/employees')">返回员工列表</el-button>
          <el-button v-if="selected.length" type="primary" @click="batchConfirm">批量确认入职 ({{ selected.length }})</el-button>
        </div>
      </div>

      <!-- 筛选标签 -->
      <div class="filter-tags">
        <el-radio-group v-model="filterType" size="small">
          <el-radio-button v-for="opt in filterOptions" :key="opt.value" :label="opt.value">
            {{ opt.label }}
            <span v-if="counts[opt.value]" class="filter-count">{{ counts[opt.value] }}</span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- Table -->
      <div class="hw-table-wrap">
        <el-table :data="candidates" v-loading="loading" style="width:100%"
          @selection-change="(s: any[]) => selected = s.map((x: any) => x.id)"
          :header-cell-style="{ background: '#F8FAFC', color: '#6B7280', fontWeight: 500, borderBottom: '1px solid #E5E7EB', fontSize: '13px', padding: '10px 12px' }"
          :cell-style="{ borderBottom: '1px solid #F3F4F6', padding: '12px 12px' }">
          <el-table-column type="selection" width="40" />
          <el-table-column label="变化类型" width="110"><template #default="{row}"><el-tag :type="typeTag[row.candidate_type] || 'info'" size="small">{{ typeLabel[row.candidate_type] || row.candidate_type }}</el-tag></template></el-table-column>
          <el-table-column label="姓名" width="100"><template #default="{row}"><strong>{{ row.employee_name }}</strong></template></el-table-column>
          <el-table-column label="编号" width="100">{{ row.employee_no }}</el-table-column>
          <el-table-column label="当前信息" min-width="160"><template #default="{row}">{{ row.old_data?.department || '' }} {{ row.old_data?.position || '' }}</template></el-table-column>
          <el-table-column label="新信息" min-width="160"><template #default="{row}">{{ row.new_data?.department || row.department || '' }} {{ row.new_data?.position || row.position || '' }}</template></el-table-column>
          <el-table-column label="检测原因" min-width="200"><template #default="{row}">{{ row.detection_reason }}</template></el-table-column>
          <el-table-column label="来源月份" width="90">{{ row.salary_month }}</el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{row}">
              <div class="tc-actions" @click.stop>
                <el-button v-if="row.candidate_type === 'POSSIBLE_HIRE'" size="small" type="primary" @click="handleAction(row, 'CONFIRM_HIRE')">确认入职</el-button>
                <el-button v-if="row.candidate_type === 'POSSIBLE_TERMINATION'" size="small" type="danger" @click="handleAction(row, 'CONFIRM_TERMINATION')">确认离职</el-button>
                <el-button v-if="row.candidate_type === 'POSSIBLE_TERMINATION'" size="small" @click="handleAction(row, 'KEEP_ACTIVE')">保持在职</el-button>
                <el-button v-if="row.candidate_type === 'DEPARTMENT_CHANGE' || row.candidate_type === 'POSITION_CHANGE'" size="small" type="warning" @click="handleAction(row, 'CONFIRM_TRANSFER')">确认调岗</el-button>
                <el-button v-if="row.candidate_type === 'INFO_CONFLICT'" size="small" @click="handleAction(row, 'CONFIRM_HIRE')">处理</el-button>
                <el-button size="small" @click="handleAction(row, 'IGNORE')">忽略</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-tags { margin-bottom: 14px; }
.filter-count { margin-left: 4px; color: var(--text-tertiary); font-size: 12px; }
.cand-stats { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.cand-stat { display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; }
.cand-stat.stat-urgent { border-color: #FCA5A5; background: #FFF5F5; }
.stat-label { color: var(--text-secondary); }
.stat-num { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.tc-actions { display: flex; gap: 4px; flex-wrap: wrap; }
.hw-table-wrap { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: visible; margin-bottom: 24px; }
</style>
