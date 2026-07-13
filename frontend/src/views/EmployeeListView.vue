<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const activeTab = ref('active')
const employees = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const keyword = ref('')
const stats = ref<any>({})
const currentMonth = ref('')
const detailDrawer = ref(false)
const selectedEmployee = ref<any>(null)
const detailTab = ref('basic')
const totalCount = ref(0)

onMounted(() => {
  const now = new Date()
  currentMonth.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  loadStats()
  loadEmployees()
})

async function loadStats() {
  try {
    
    const res = await fetch('/api/v1/employees/stats/overview', {
      headers: {},
    })
    const json = await res.json()
    if (json.success) stats.value = json.data || {}
  } catch {}
}

async function loadEmployees() {
  loading.value = true
  try {
    
    const params = new URLSearchParams({ page: String(page.value), page_size: '50' })
    if (keyword.value) params.set('keyword', keyword.value)
    // Active tab affects status filter
    if (activeTab.value === 'active') params.set('status', 'ACTIVE')
    else if (activeTab.value === 'resigned') params.set('status', 'RESIGNED')
    else if (activeTab.value === 'all') params.set('include_resigned', 'true')

    const res = await fetch(`/api/v1/employees?${params}`, {
      headers: {},
    })
    const json = await res.json()
    if (json.success) {
      employees.value = json.data.items || []
      totalCount.value = json.data.total || 0
    }
  } catch { ElMessage.error('获取失败') }
  finally { loading.value = false }
}

function onTabChange(tab: string) {
  activeTab.value = tab
  page.value = 1
  loadEmployees()
}

function handleSearch() { page.value = 1; loadEmployees() }

function employeeFieldStatus(emp: any): { status: 'COMPLETE' | 'INCOMPLETE' | 'CONFLICT'; missing: string[] } {
  const missing: string[] = []
  if (!emp.employee_no) missing.push('员工编号')
  if (!emp.department) missing.push('部门')
  if (!emp.position) missing.push('岗位')
  if (!emp.salary_standard) missing.push('工资标准')
  return {
    status: missing.length === 0 ? 'COMPLETE' : 'INCOMPLETE',
    missing,
  }
}

function attendanceStatus(emp: any): { label: string; type: string } {
  if (emp.status !== 'ACTIVE') return { label: '已离职', type: 'info' }
  return { label: '已匹配考勤', type: 'success' }
}

function openDetail(emp: any) {
  selectedEmployee.value = emp
  detailDrawer.value = true
  detailTab.value = 'basic'
}

async function handleResign(emp: any) {
  try {
    const { value } = await ElMessageBox.prompt(
      `办理离职 - ${emp.employee_name}`,
      '办理离职',
      { confirmButtonText: '确认离职', cancelButtonText: '取消',
        inputPlaceholder: '离职日期 YYYY-MM-DD',
        inputValidator: (v: string) => v && v.trim().length >= 10 ? true : '请输入离职日期' }
    )
    
    const res = await fetch(`/api/v1/employees/${emp.id}/resign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resign_date: value, reason: '管理员操作' }),
    })
    const json = await res.json()
    if (json.success) { ElMessage.success('已办理离职'); await loadEmployees(); await loadStats() }
    else { ElMessage.error(json.message || '操作失败') }
  } catch {}
}

async function handleAction(emp: any, cmd: string) {
  if (cmd === 'detail') openDetail(emp)
  else if (cmd === 'resign') await handleResign(emp)
}

const tabCounts = computed(() => ({
  changes: stats.value.pending_candidates || 0,
  active: stats.value.active || 0,
  resigned: stats.value.resigned || 0,
  total: (stats.value.active || 0) + (stats.value.resigned || 0),
}))

const pendingSummary = computed(() => {
  const parts: string[] = []
  if (stats.value.pending_hire) parts.push(`${stats.value.pending_hire}条疑似入职`)
  if (stats.value.pending_termination) parts.push(`${stats.value.pending_termination}条疑似离职`)
  if (stats.value.pending_department_change) parts.push(`${stats.value.pending_department_change}条岗位/部门变化`)
  if (stats.value.pending_conflict) parts.push(`${stats.value.pending_conflict}条信息冲突`)
  return parts.join('，')
})

// 流程步骤状态
const flowSteps = computed(() => {
  const steps = []
  // 步骤1: 上传考勤人员
  steps.push({
    label: '上传考勤人员',
    status: 'completed',
    text: '已上传',
  })
  // 步骤2: 识别人员变化
  const hasChanges = (stats.value.pending_candidates || 0) > 0
  steps.push({
    label: '识别人员变化',
    status: hasChanges ? 'processing' : 'completed',
    text: hasChanges ? `发现${stats.value.pending_candidates}条变化` : '已完成',
  })
  // 步骤3: 确认员工异动
  steps.push({
    label: '确认员工异动',
    status: hasChanges ? 'pending' : 'completed',
    text: hasChanges ? `待确认${stats.value.pending_candidates}条` : '已确认',
  })
  // 步骤4: 同步工资人员
  steps.push({
    label: '同步工资人员',
    status: 'pending',
    text: '待同步',
  })
  return steps
})
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <!-- 标题区 -->
      <div class="emp-header">
        <div class="emp-header-left">
          <h1 class="page-title" style="margin:0 0 2px">员工档案</h1>
          <p class="page-subtitle" style="margin:0">
            通过每月考勤人员数据识别员工入职、离职及岗位变化，确认后同步员工档案和本月工资人员范围
          </p>
        </div>
        <div class="emp-header-actions">
          <el-tag type="info" effect="plain" style="margin-right:8px">{{ currentMonth }}</el-tag>
          <el-button @click="router.push('/employees/import-attendance')">
            <el-icon><Upload /></el-icon>导入本月考勤
          </el-button>
          <el-button type="primary">
            <el-icon><Plus /></el-icon>手动新增员工
          </el-button>
        </div>
      </div>

      <!-- 流程步骤条 -->
      <div class="emp-flow">
        <template v-for="(step, idx) in flowSteps" :key="idx">
          <div class="flow-step" :class="{ active: step.status === 'processing' }">
            <span class="fs-num" :class="{
              done: step.status === 'completed',
              warn: step.status === 'processing',
              pending: step.status === 'pending'
            }">
              {{ step.status === 'completed' ? '✓' : step.status === 'processing' ? '!' : (idx + 1) }}
            </span>
            <span class="fs-label">{{ step.label }}</span>
            <span class="fs-status" :class="step.status">{{ step.text }}</span>
          </div>
          <div v-if="idx < flowSteps.length - 1" class="flow-arrow">→</div>
        </template>
      </div>

      <!-- 待确认提醒 -->
      <div v-if="stats.pending_candidates" class="emp-alert">
        <el-icon :size="16" style="color:#D97706"><WarningFilled /></el-icon>
        <span>本月发现 {{ pendingSummary }}，建议在创建工资任务前完成确认。</span>
        <el-button size="small" style="margin-left:auto" @click="router.push('/employees/changes')">前往处理</el-button>
      </div>

      <!-- 统计卡片 -->
      <div class="emp-stats">
        <div class="e-card" @click="activeTab = 'active'; loadEmployees()">
          <span class="ec-label">本月考勤人数</span>
          <span class="ec-value ec-blue">{{ stats.active || 0 }}</span>
        </div>
        <div class="e-card" @click="activeTab = 'active'; loadEmployees()">
          <span class="ec-label">当前在职人数</span>
          <span class="ec-value ec-blue">{{ stats.active || 0 }}</span>
        </div>
        <div class="e-card" v-if="stats.pending_hire" @click="router.push('/employees/changes')">
          <span class="ec-label">疑似新入职</span>
          <span class="ec-value ec-orange">{{ stats.pending_hire }}</span>
        </div>
        <div class="e-card" v-if="stats.pending_termination" @click="router.push('/employees/changes')">
          <span class="ec-label">疑似离职</span>
          <span class="ec-value ec-red">{{ stats.pending_termination }}</span>
        </div>
        <div class="e-card" v-if="stats.pending_conflict" @click="router.push('/employees/changes')">
          <span class="ec-label">信息冲突</span>
          <span class="ec-value ec-red">{{ stats.pending_conflict }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="emp-tabs">
        <div class="tab-item" :class="{ active: activeTab === 'changes' }" @click="router.push('/employees/changes')">
          本月人员变化 <span class="tab-badge" v-if="tabCounts.changes">{{ tabCounts.changes }}</span>
        </div>
        <div class="tab-item" :class="{ active: activeTab === 'active' }" @click="onTabChange('active')">
          在职员工 <span class="tab-badge muted">{{ tabCounts.active }}</span>
        </div>
        <div class="tab-item" :class="{ active: activeTab === 'resigned' }" @click="onTabChange('resigned')">
          已离职员工 <span class="tab-badge muted">{{ tabCounts.resigned }}</span>
        </div>
        <div class="tab-item" :class="{ active: activeTab === 'all' }" @click="onTabChange('all')">
          全部档案 <span class="tab-badge muted">{{ tabCounts.total }}</span>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="emp-toolbar">
        <el-input v-model="keyword" placeholder="搜索姓名或编号" clearable style="width:220px" @keyup.enter="handleSearch" />
        <div class="et-right">
          <span class="et-count">共 {{ totalCount }} 人</span>
          <el-button type="primary" size="small" @click="handleSearch">查询</el-button>
        </div>
      </div>

      <!-- Table -->
      <div class="emp-table">
        <el-table :data="employees" v-loading="loading" style="width:100%" @row-click="openDetail"
          :header-cell-style="{ background: '#F8FAFC', color: '#6B7280', fontWeight: 500, borderBottom: '1px solid #E5E7EB', fontSize: '13px', padding: '10px 12px' }"
          :cell-style="{ borderBottom: '1px solid #F3F4F6', padding: '12px 12px' }">
          <el-table-column label="员工" min-width="160">
            <template #default="{row}">
              <div class="tc-name">
                <strong>{{ row.employee_name }}</strong>
                <span class="tc-sub">{{ row.employee_no || '无编号' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="部门/岗位" min-width="160">
            <template #default="{row}">
              <div v-if="row.department || row.position">
                {{ row.department || '—' }} · {{ row.position || '—' }}
              </div>
              <span v-else class="tc-missing">待补全</span>
            </template>
          </el-table-column>
          <el-table-column label="入职信息" width="170">
            <template #default="{row}">
              <span>{{ row.hire_date || '—' }}</span>
              <span v-if="row.resign_date" class="tc-resign"> ~ {{ row.resign_date }}</span>
            </template>
          </el-table-column>
          <el-table-column label="工资标准" width="120" align="right">
            <template #default="{row}">
              <span v-if="row.salary_standard">¥{{ Number(row.salary_standard).toLocaleString() }}</span>
              <span v-else class="tc-missing">待补全</span>
            </template>
          </el-table-column>
          <el-table-column label="档案状态" width="100">
            <template #default="{row}">
              <el-tag v-if="row.status === 'ACTIVE'" size="small" type="success" effect="plain">在职</el-tag>
              <el-tag v-else size="small" type="info" effect="plain">已离职</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{row}">
              <div class="tc-actions" @click.stop>
                <el-button size="small" text @click="openDetail(row)">查看</el-button>
                <el-dropdown trigger="click" @command="(cmd:string) => handleAction(row, cmd)">
                  <el-button size="small" text><el-icon><MoreFilled /></el-icon></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="detail">编辑档案</el-dropdown-item>
                      <el-dropdown-item command="detail">调整岗位</el-dropdown-item>
                      <el-dropdown-item command="detail">调整薪资</el-dropdown-item>
                      <el-dropdown-item v-if="row.status === 'ACTIVE'" command="resign" divided style="color:#DC2626">办理离职</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div v-if="employees.length > 0" class="emp-page">
        <el-pagination v-model:current-page="page" :total="totalCount"
          :page-size="50" layout="prev, pager, next" background small @change="loadEmployees" />
      </div>

      <!-- 详情抽屉 -->
      <el-drawer v-model="detailDrawer" :title="selectedEmployee?.employee_name" size="45%" direction="rtl">
        <template v-if="selectedEmployee">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="基础档案" name="basic">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="员工编号">{{ selectedEmployee.employee_no || '—' }}</el-descriptions-item>
                <el-descriptions-item label="姓名">{{ selectedEmployee.employee_name }}</el-descriptions-item>
                <el-descriptions-item label="部门">{{ selectedEmployee.department || '—' }}</el-descriptions-item>
                <el-descriptions-item label="岗位">{{ selectedEmployee.position || '—' }}</el-descriptions-item>
                <el-descriptions-item label="入职日期">{{ selectedEmployee.hire_date || '—' }}</el-descriptions-item>
                <el-descriptions-item label="离职日期">{{ selectedEmployee.resign_date || '—' }}</el-descriptions-item>
                <el-descriptions-item label="状态">{{ selectedEmployee.status === 'ACTIVE' ? '在职' : '已离职' }}</el-descriptions-item>
                <el-descriptions-item label="工资标准">{{ selectedEmployee.salary_standard ? `¥${Number(selectedEmployee.salary_standard).toLocaleString()}` : '—' }}</el-descriptions-item>
                <el-descriptions-item label="档案来源">{{ selectedEmployee.source_type || '—' }}</el-descriptions-item>
              </el-descriptions>
            </el-tab-pane>
            <el-tab-pane label="任职记录" name="position">
              <el-empty description="暂无任职记录" />
            </el-tab-pane>
            <el-tab-pane label="薪资记录" name="salary">
              <el-empty description="暂无薪资记录" />
            </el-tab-pane>
            <el-tab-pane label="月度考勤" name="attendance">
              <el-empty description="暂无考勤记录" />
            </el-tab-pane>
            <el-tab-pane label="月度工资" name="payroll">
              <el-empty description="暂无工资记录" />
            </el-tab-pane>
            <el-tab-pane label="变更日志" name="logs">
              <el-empty description="暂无变更记录" />
            </el-tab-pane>
          </el-tabs>
        </template>
      </el-drawer>
    </div>
  </div>
</template>

<style scoped>
.emp-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 20px 0 14px; }
.emp-header-left { flex: 1; }
.emp-header-actions { display: flex; align-items: center; flex-shrink: 0; }

/* 流程步骤条 */
.emp-flow { display: flex; align-items: center; gap: 4px; padding: 12px 18px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; }
.flow-step { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.flow-step.active .fs-label { font-weight: 600; color: #2563EB; }
.fs-num { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; background: #F3F4F6; color: #9CA3AF; }
.fs-num.done { background: #DCFCE7; color: #16A34A; }
.fs-num.warn { background: #FEF3C7; color: #D97706; }
.fs-num.pending { background: #F3F4F6; color: #9CA3AF; }
.fs-label { color: var(--text-primary); }
.fs-status { font-size: 11px; color: var(--text-tertiary); padding: 1px 6px; border-radius: 4px; background: #F3F4F6; }
.fs-status.completed { background: #DCFCE7; color: #16A34A; }
.fs-status.processing { background: #FEF3C7; color: #D97706; }
.fs-status.pending { background: #F3F4F6; color: #9CA3AF; }
.flow-arrow { color: var(--border); font-size: 14px; }

/* 提醒 */
.emp-alert { display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; font-size: 13px; color: #92400E; margin-bottom: 12px; }

/* 统计 */
.emp-stats { display: flex; gap: 10px; margin-bottom: 14px; }
.e-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; cursor: pointer; transition: border-color .15s; }
.e-card:hover { border-color: #2563EB; }
.ec-label { display: block; font-size: 12px; color: var(--text-tertiary); }
.ec-value { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1.3; }
.ec-blue { color: #2563EB; }
.ec-orange { color: #D97706; }
.ec-red { color: #DC2626; }

/* Tabs */
.emp-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 0; }
.tab-item { padding: 10px 18px; font-size: 14px; color: var(--text-secondary); cursor: pointer; border-bottom: 2px solid transparent; transition: all .12s; display: flex; align-items: center; gap: 6px; }
.tab-item:hover { color: var(--text-primary); }
.tab-item.active { color: #2563EB; border-bottom-color: #2563EB; font-weight: 500; }
.tab-badge { font-size: 11px; padding: 0 6px; background: #DBEAFE; color: #2563EB; border-radius: 10px; line-height: 18px; }
.tab-badge.muted { background: #F3F4F6; color: #9CA3AF; }

/* Toolbar */
.emp-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; gap: 12px; }
.et-right { display: flex; align-items: center; gap: 8px; }
.et-count { font-size: 13px; color: var(--text-tertiary); }

/* Table */
.emp-table { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: visible; }
.tc-name { display: flex; flex-direction: column; gap: 1px; cursor: pointer; }
.tc-sub { font-size: 12px; color: var(--text-tertiary); font-family: monospace; }
.tc-missing { font-size: 12px; color: #D97706; font-style: italic; }
.tc-resign { color: #DC2626; font-size: 12px; }
.tc-actions { display: flex; align-items: center; gap: 2px; }
.emp-page { display: flex; justify-content: flex-end; padding: 10px 0 20px; }

/* No empty data styles - use native el-empty */
</style>
