<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElDrawer } from 'element-plus'
import { employeeApi, importApi } from '@/api'
import { formatMoney, formatDate } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const employees = ref<any[]>([])
const files = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')

// 详情抽屉
const drawerVisible = ref(false)
const selectedEmployee = ref<any>(null)
const selectedField = ref<string>('')

const DATA_FIELDS = [
  { key: 'base_salary', label: '基本工资', source: '基础薪资' },
  { key: 'attendance_days', label: '出勤天数', source: '考勤' },
  { key: 'attendance_deduction', label: '考勤扣款', source: '考勤' },
  { key: 'performance_bonus', label: '绩效奖金', source: '绩效' },
  { key: 'meal_allowance', label: '餐补', source: '补贴' },
  { key: 'traffic_allowance', label: '交通补贴', source: '补贴' },
  { key: 'communication_allowance', label: '通讯补贴', source: '补贴' },
  { key: 'social_security_personal', label: '社保个人扣款', source: '社保' },
  { key: 'housing_fund_personal', label: '公积金个人扣款', source: '社保' },
  { key: 'other_deduction', label: '其他扣款', source: '其他调整' },
]

// 按数据来源分组
const DATA_SOURCES = [
  { key: 'base', label: '基础薪资', icon: 'UserFilled', fields: ['base_salary'] },
  { key: 'attendance', label: '考勤', icon: 'Calendar', fields: ['attendance_days', 'attendance_deduction'] },
  { key: 'performance', label: '绩效', icon: 'TrendCharts', fields: ['performance_bonus'] },
  { key: 'subsidy', label: '补贴', icon: 'Money', fields: ['meal_allowance', 'traffic_allowance', 'communication_allowance'] },
  { key: 'social', label: '社保公积金', icon: 'Shield', fields: ['social_security_personal', 'housing_fund_personal'] },
  { key: 'other', label: '其他调整', icon: 'EditPen', fields: ['other_deduction'] },
]

onMounted(async () => {
  await Promise.all([fetchEmployees(), fetchFiles()])
})

async function fetchEmployees() {
  loading.value = true
  try {
    const res = await employeeApi.list(runId, { keyword: keyword.value || undefined })
    employees.value = res.data.data.items || []
  } catch {
    ElMessage.error('获取员工列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchFiles() {
  try {
    const res = await importApi.getFiles(runId)
    files.value = res.data.data.items || []
  } catch {
    // ignore
  }
}

const filteredEmployees = computed(() => {
  if (!keyword.value) return employees.value
  const kw = keyword.value.toLowerCase()
  return employees.value.filter((e: any) => e.employee_name?.toLowerCase().includes(kw))
})

// 检查某员工某个来源是否完整
function isSourceComplete(employee: any, sourceKey: string): boolean | null {
  const source = DATA_SOURCES.find((s) => s.key === sourceKey)
  if (!source) return null
  // 检查该来源的所有字段是否都有值
  const fieldKeys = source.fields
  const fields = employee.fields || {}
  const hasAny = fieldKeys.some((fk) => {
    const val = fields[fk]
    return val !== undefined && val !== null && val !== '' && val !== '0'
  })
  // 没有数据返回 null（表示不适用）
  if (!hasAny) return null
  // 有部分数据
  const allPresent = fieldKeys.every((fk) => {
    const val = fields[fk]
    return val !== undefined && val !== null && val !== ''
  })
  return allPresent
}

// 统计数据概况
const summaryStats = computed(() => {
  const total = employees.value.length
  const result: Record<string, { complete: number; partial: number; missing: number }> = {}

  for (const source of DATA_SOURCES) {
    let complete = 0
    let partial = 0
    let missing = 0

    for (const emp of employees.value) {
      const status = isSourceComplete(emp, source.key)
      if (status === true) complete++
      else if (status === false) partial++
      else missing++
    }

    result[source.key] = { complete, partial, missing }
  }

  // 整体完整度
  const allComplete = employees.value.filter((emp: any) => {
    const fields = emp.fields || {}
    return DATA_SOURCES.some((s) => s.fields.some((fk) => fields[fk] !== undefined && fields[fk] !== null && fields[fk] !== ''))
  }).length

  return {
    total,
    hasData: allComplete,
    sources: result,
  }
})

function openDetail(employee: any, fieldKey: string) {
  selectedEmployee.value = employee
  selectedField.value = fieldKey
  drawerVisible.value = true
}

function getFieldSourceText(fieldKey: string): string {
  // 简单映射字段来源
  const source = DATA_FIELDS.find((f) => f.key === fieldKey)
  return source?.source || '系统'
}

function getSourceStat(sourceKey: string): string {
  const stat = summaryStats.value.sources[sourceKey]
  if (!stat) return ''
  const parts = []
  if (stat.complete > 0) parts.push(`${stat.complete}人完整`)
  if (stat.partial > 0) parts.push(`${stat.partial}人异常`)
  if (stat.missing > 0 && stat.missing < summaryStats.value.total) parts.push(`${stat.missing}人无数据`)
  return parts.join(' · ')
}

function handleSearch() {
  fetchEmployees()
}

// Source color mapping
const SOURCE_COLORS: Record<string, string> = {
  base: '#2563EB',
  attendance: '#7C3AED',
  performance: '#D97706',
  subsidy: '#059669',
  social: '#0891B2',
  other: '#DC2626',
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
        <span>数据汇总</span>
      </div>

      <!-- 页面标题 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">数据汇总确认</h1>
          <p class="page-subtitle">确认每个员工各数据来源的完整性和准确性</p>
        </div>
        <div style="display:flex; gap:8px">
          <el-button @click="fetchEmployees">
            <el-icon style="margin-right:4px"><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>

      <!-- 数据源概览卡片 -->
      <div class="stat-cards">
        <div class="stat-card" style="height:auto; min-height:80px; flex-direction:column; align-items:flex-start; gap:6px; padding:14px 18px">
          <div class="stat-card-label">员工总数</div>
          <div class="stat-card-value">{{ summaryStats.total }}</div>
        </div>
        <div
          v-for="source in DATA_SOURCES"
          :key="source.key"
          class="stat-card"
          style="height:auto; min-height:80px; flex-direction:column; align-items:flex-start; gap:6px; padding:14px 18px"
        >
          <div style="display:flex; align-items:center; gap:6px">
            <span :style="{ width:'8px', height:'8px', borderRadius:'50%', background: SOURCE_COLORS[source.key] }" />
            <span class="stat-card-label">{{ source.label }}</span>
          </div>
          <div class="stat-card-value" style="font-size:18px">{{ getSourceStat(source.key) }}</div>
        </div>
      </div>

      <!-- 数据表格 -->
      <div class="content-card" style="padding:0; overflow:hidden">
        <!-- 搜索 -->
        <div style="display:flex; align-items:center; gap:12px; padding:14px 18px; border-bottom:1px solid var(--border)">
          <el-input v-model="keyword" placeholder="搜索员工姓名" clearable style="width:220px" @keyup.enter="handleSearch" />
          <el-button @click="handleSearch"><el-icon><Search /></el-icon>查询</el-button>
          <span style="color:var(--text-tertiary); font-size:13px">共 {{ filteredEmployees.length }} 名员工</span>
        </div>

        <el-table :data="filteredEmployees" v-loading="loading" stripe style="width:100%">
          <el-table-column prop="employee_name" label="员工姓名" width="130" fixed>
            <template #default="{ row }">
              <span style="font-weight:500; color:var(--text-primary)">{{ row.employee_name }}</span>
            </template>
          </el-table-column>

          <!-- 每个数据源一列 -->
          <el-table-column v-for="source in DATA_SOURCES" :key="source.key" :label="source.label" min-width="110" align="center">
            <template #default="{ row }">
              <div class="source-cell" :class="{ 'cell-complete': isSourceComplete(row, source.key) === true, 'cell-partial': isSourceComplete(row, source.key) === false, 'cell-missing': isSourceComplete(row, source.key) === null }">
                <template v-if="isSourceComplete(row, source.key) === true">
                  <el-icon :size="16" style="color:var(--success)"><CircleCheck /></el-icon>
                  <span style="font-size:13px; color:var(--text-secondary)">完整</span>
                </template>
                <template v-else-if="isSourceComplete(row, source.key) === false">
                  <el-icon :size="16" style="color:var(--warning)"><WarningFilled /></el-icon>
                  <span style="font-size:13px; color:var(--warning)">异常</span>
                </template>
                <template v-else>
                  <span style="font-size:13px; color:var(--text-tertiary)">--</span>
                </template>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="100" fixed="right">
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'NORMAL' ? 'success' : 'warning'"
                size="small"
                effect="plain"
              >
                {{ row.status === 'NORMAL' ? '正常' : row.status === 'NAME_DUPLICATE' ? '重名' : row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && filteredEmployees.length === 0" description="暂无员工数据" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.el-table .cell-complete {
  color: var(--success);
}
</style>
