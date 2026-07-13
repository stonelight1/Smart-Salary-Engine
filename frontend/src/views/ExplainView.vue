<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { calcApi, employeeApi } from '@/api'
import { formatMoney, formatDate } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const employees = ref<any[]>([])
const selectedEmp = ref(route.query.emp as string || '')
const explainData = ref<any>(null)
const loading = ref(false)
const empLoading = ref(false)

// 工资介绍类型分类
const CATEGORIES = {
  income: { title: '收入项目', icon: 'Money' },
  deduction: { title: '个人扣款', icon: 'Remove' },
  total: { title: '最终结果', icon: 'Document' },
}

function getItemCategory(item: { item_code: string }): string {
  const incomeCodes = ['performance_bonus', 'allowance_total']
  const deductionCodes = ['attendance_deduction', 'other_deduction', 'social_security_personal', 'housing_fund_personal']
  const totalCodes = ['gross_salary', 'deduction_total', 'net_salary']

  if (incomeCodes.includes(item.item_code)) return 'income'
  if (deductionCodes.includes(item.item_code)) return 'deduction'
  if (totalCodes.includes(item.item_code)) return 'total'
  return 'other'
}

// 被折叠解释记录
const expandedItems = ref<Set<string>>(new Set())

function toggleItem(code: string) {
  if (expandedItems.value.has(code)) {
    expandedItems.value.delete(code)
  } else {
    expandedItems.value.add(code)
  }
}

function isExpanded(code: string): boolean {
  return expandedItems.value.has(code)
}

onMounted(async () => {
  empLoading.value = true
  try {
    const res = await employeeApi.list(runId)
    employees.value = res.data.data.items || []
    if (!selectedEmp.value && employees.value.length > 0) {
      selectedEmp.value = employees.value[0].employee_ref_id
    }
    if (selectedEmp.value) {
      await loadExplain()
    }
  } catch {
    ElMessage.error('获取员工列表失败')
  } finally {
    empLoading.value = false
  }
})

async function loadExplain() {
  if (!selectedEmp.value) return
  loading.value = true
  try {
    const res = await calcApi.getExplain(runId, selectedEmp.value)
    explainData.value = res.data.data
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '获取解释失败')
  } finally {
    loading.value = false
  }
}

const selectedName = computed(() => {
  const emp = employees.value.find((e: any) => e.employee_ref_id === selectedEmp.value)
  return emp?.employee_name || '未知'
})

const currentEmpIndex = computed(() => {
  return employees.value.findIndex((e: any) => e.employee_ref_id === selectedEmp.value)
})

function prevEmployee() {
  const idx = currentEmpIndex.value
  if (idx > 0) {
    selectedEmp.value = employees.value[idx - 1].employee_ref_id
    loadExplain()
  }
}

function nextEmployee() {
  const idx = currentEmpIndex.value
  if (idx < employees.value.length - 1) {
    selectedEmp.value = employees.value[idx + 1].employee_ref_id
    loadExplain()
  }
}

// 分组数据
const groupedItems = computed(() => {
  if (!explainData.value?.items) return {}
  const groups: Record<string, any[]> = { income: [], deduction: [], total: [], other: [] }

  for (const item of explainData.value.items) {
    const cat = getItemCategory(item)
    groups[cat].push(item)
  }

  // total 组按指定顺序排列
  const totalOrder = ['gross_salary', 'deduction_total', 'net_salary']
  groups.total.sort((a: any, b: any) => {
    return totalOrder.indexOf(a.item_code) - totalOrder.indexOf(b.item_code)
  })

  return groups
})

// 摘要数据
const summaryData = computed(() => {
  if (!explainData.value) return null
  const items = explainData.value.items || []
  const getAmount = (code: string) => {
    const item = items.find((i: any) => i.item_code === code)
    return item ? formatMoney(item.amount) : '--'
  }

  return {
    netSalary: formatMoney(explainData.value.net_salary),
    grossSalary: getAmount('gross_salary'),
    deductionTotal: getAmount('deduction_total'),
    calcVersion: explainData.value.calc_version,
  }
})

// 判断某个 input 值是否为空或 0
function isEmptyValue(val: string): boolean {
  return val === '' || val === null || val === undefined || val === '0' || val === '0.000000'
}

// 格式化输入值展示
function formatInputValue(val: string): string {
  if (val === '' || val === null || val === undefined) return '未填写'
  const num = Number(val)
  if (isNaN(num)) return val || '未填写'
  // 金额字段
  return formatMoney(val)
}

// 分类提示
function categorizeInput(code: string): string {
  const allowanceCodes = ['meal_allowance', 'traffic_allowance', 'communication_allowance']
  const bonusCodes = ['performance_bonus']
  const baseCodes = ['base_salary']
  if (allowanceCodes.includes(code)) return 'allowance'
  if (bonusCodes.includes(code)) return 'bonus'
  if (baseCodes.includes(code)) return 'base'
  if (code === 'attendance_deduction') return 'attendance'
  if (['other_deduction', 'social_security_personal', 'housing_fund_personal'].includes(code)) return 'deduction'
  return 'other'
}

// 复制解释
async function copyExplain() {
  if (!explainData.value) return

  const empName = explainData.value.employee_name
  const month = '本月' // 通用文本
  const items = explainData.value.items || []

  let text = `${empName} 工资解释\n\n`

  // 收入
  const grossItem = items.find((i: any) => i.item_code === 'gross_salary')
  if (grossItem) {
    text += `应发工资：${formatMoney(grossItem.amount)}元\n`
    text += '其中：\n'
    for (const input of grossItem.inputs || []) {
      if (!isEmptyValue(input.value)) {
        const name = getInputDisplayName(input.field_code)
        text += `- ${name}：${formatMoney(input.value)}元\n`
      }
    }
    text += '\n'
  }

  // 扣款
  const deductionItem = items.find((i: any) => i.item_code === 'deduction_total')
  if (deductionItem) {
    text += `扣款合计：${formatMoney(deductionItem.amount)}元\n`
    for (const input of deductionItem.inputs || []) {
      if (!isEmptyValue(input.value)) {
        const name = getInputDisplayName(input.field_code)
        text += `- ${name}：${formatMoney(input.value)}元\n`
      }
    }
    text += '\n'
  }

  text += `实发工资：${formatMoney(explainData.value.net_salary)}元`

  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制工资解释')
  } catch {
    ElMessage.error('复制失败')
  }
}

function getInputDisplayName(fieldCode: string): string {
  const nameMap: Record<string, string> = {
    base_salary: '基本工资',
    performance_bonus: '绩效奖金',
    allowance_total: '补贴合计',
    meal_allowance: '餐补',
    traffic_allowance: '交通补贴',
    communication_allowance: '通讯补贴',
    attendance_deduction: '考勤扣款',
    other_deduction: '其他扣款',
    social_security_personal: '社保个人扣款',
    housing_fund_personal: '公积金个人扣款',
    gross_salary: '应发工资',
    deduction_total: '扣款合计',
    net_salary: '实发工资',
  }
  return nameMap[fieldCode] || fieldCode
}

function getCategoryTotal(cat: string): string {
  const items = groupedItems.value[cat] || []
  let total = 0
  for (const item of items) {
    total += parseFloat(item.amount || '0')
  }
  return total > 0 ? formatMoney(total) : '--'
}

// 友好的公式说明
function getFormulaDescription(item: { item_code: string; formula: string }): string {
  if (!item.formula) return ''
  const descMap: Record<string, string> = {
    performance_bonus: '未填写绩效奖金时按 0 元计算',
    allowance_total: '餐补、交通补贴和通讯补贴相加',
    attendance_deduction: '未填写考勤扣款时按 0 元计算',
    other_deduction: '未填写其他扣款时按 0 元计算',
    social_security_personal: '未填写社保个人扣款时按 0 元计算',
    housing_fund_personal: '未填写公积金个人扣款时按 0 元计算',
    gross_salary: '基本工资 + 绩效奖金 + 补贴合计 - 考勤扣款',
    deduction_total: '其他扣款 + 社保个人扣款 + 公积金个人扣款',
    net_salary: '应发工资 - 扣款合计',
  }
  return descMap[item.item_code] || item.formula
}

// 检查输入是否有异常（为空或 0，但预期的值可能为空）
function hasEmptyInput(item: any): boolean {
  if (!item.inputs) return false
  return item.inputs.some((input: any) => isEmptyValue(input.value))
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
        <span>工资解释</span>
      </div>

      <!-- 页面头部 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">工资解释</h1>
          <p class="page-subtitle">查看员工工资构成、扣款原因和计算过程</p>
        </div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap">
          <el-button @click="router.push(`/runs/${runId}`)">
            <el-icon style="margin-right:4px"><Back /></el-icon>
            返回任务
          </el-button>
        </div>
      </div>

      <!-- 员工选择器 -->
      <div class="employee-selector-bar">
        <div class="emp-select-left">
          <el-select
            v-model="selectedEmp"
            filterable
            placeholder="搜索员工"
            style="width:240px"
            @change="loadExplain"
            :loading="empLoading"
          >
            <el-option
              v-for="e in employees"
              :key="e.employee_ref_id"
              :label="e.employee_name"
              :value="e.employee_ref_id"
            />
          </el-select>
          <div class="emp-nav">
            <el-button :disabled="currentEmpIndex <= 0" text @click="prevEmployee">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <span class="emp-nav-text">
              {{ currentEmpIndex >= 0 ? currentEmpIndex + 1 : 0 }}/{{ employees.length }}
            </span>
            <el-button :disabled="currentEmpIndex >= employees.length - 1" text @click="nextEmployee">
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
        <div>
          <el-button size="default" @click="copyExplain">
            <el-icon style="margin-right:4px"><CopyDocument /></el-icon>
            复制解释
          </el-button>
        </div>
      </div>

      <div v-loading="loading">
        <template v-if="explainData">
          <!-- 员工工资总览卡片 -->
          <div class="salary-overview">
            <div class="overview-left">
              <div class="overview-emp-info">
                <span class="overview-emp-name">{{ explainData.employee_name }}</span>
                <span v-if="explainData.employee_department" class="overview-emp-dept">{{ explainData.employee_department }}</span>
              </div>
              <div class="text-tertiary" style="font-size:13px">
                计算版本 v{{ summaryData?.calcVersion || '-' }}
              </div>
            </div>
            <div class="overview-center">
              <div class="overview-label">实发工资</div>
              <div class="overview-amount">¥{{ summaryData?.netSalary || '--' }}</div>
            </div>
            <div class="overview-right">
              <div class="overview-stat-item">
                <span class="overview-stat-label">应发合计</span>
                <span class="overview-stat-value">¥{{ summaryData?.grossSalary || '--' }}</span>
              </div>
              <div class="overview-stat-item">
                <span class="overview-stat-label">扣款合计</span>
                <span class="overview-stat-value">¥{{ summaryData?.deductionTotal || '--' }}</span>
              </div>
            </div>
          </div>

          <!-- 两栏布局 -->
          <div class="explain-layout">
            <!-- 左侧：工资构成明细 -->
            <div class="explain-main">
              <!-- 收入项目 -->
              <div v-if="groupedItems.income && groupedItems.income.length" class="explain-section">
                <div class="section-header">
                  <el-icon :size="18" style="color:var(--success)"><Money /></el-icon>
                  <span>收入项目</span>
                </div>

                <div v-for="item in groupedItems.income" :key="item.item_code" class="salary-item-card">
                  <div class="salary-item-header">
                    <div class="salary-item-info">
                      <div class="salary-item-name">{{ item.item_name }}</div>
                      <div v-if="getFormulaDescription(item)" class="salary-item-desc">
                        {{ getFormulaDescription(item) }}
                      </div>
                    </div>
                    <div class="salary-item-amount">¥{{ formatMoney(item.amount) }}</div>
                  </div>

                  <!-- 输入值 -->
                  <div v-if="item.inputs && item.inputs.length" class="salary-item-inputs">
                    <div v-for="input in item.inputs" :key="input.field_code" class="input-row">
                      <span class="input-label">
                        {{ getInputDisplayName(input.field_code) || input.field_code }}
                      </span>
                      <span v-if="isEmptyValue(input.value)" class="input-empty">未填写</span>
                      <span v-else class="input-value">¥{{ formatInputValue(input.value) }}</span>
                    </div>
                  </div>

                  <!-- 公式折叠 -->
                  <div v-if="item.formula" class="salary-item-formula-toggle" @click="toggleItem(item.item_code)">
                    <el-icon size="12">
                      <ArrowRight v-if="!isExpanded(item.item_code)" />
                      <ArrowDown v-else />
                    </el-icon>
                    <span>查看计算公式</span>
                  </div>
                  <div v-if="isExpanded(item.item_code) && item.formula" class="salary-item-formula-detail">
                    <div class="formula-line">
                      <span class="formula-label">原始公式</span>
                      <code>{{ item.formula }}</code>
                    </div>
                    <div v-if="item.inputs && item.inputs.length" class="formula-line">
                      <span class="formula-label">字段值</span>
                      <div class="formula-values">
                        <span v-for="input in item.inputs" :key="input.field_code" class="formula-value-tag">
                          {{ getInputDisplayName(input.field_code) || input.field_code }} =
                          {{ formatInputValue(input.value) }}
                        </span>
                      </div>
                    </div>
                    <div class="formula-line">
                      <span class="formula-label">计算结果</span>
                      <span style="font-weight:600; color:var(--text-primary)">¥{{ formatMoney(item.amount) }}</span>
                    </div>
                  </div>

                  <!-- 空值警告 -->
                  <div v-if="hasEmptyInput(item)" class="salary-item-warning">
                    <el-icon :size="14" style="color:var(--warning)"><WarningFilled /></el-icon>
                    <span>部分输入值为空，已按 0 元计算</span>
                  </div>
                </div>
              </div>

              <!-- 个人扣款 -->
              <div v-if="groupedItems.deduction && groupedItems.deduction.length" class="explain-section">
                <div class="section-header">
                  <el-icon :size="18" style="color:var(--warning)"><Remove /></el-icon>
                  <span>个人扣款</span>
                </div>

                <div v-for="item in groupedItems.deduction" :key="item.item_code" class="salary-item-card">
                  <div class="salary-item-header">
                    <div class="salary-item-info">
                      <div class="salary-item-name">{{ item.item_name }}</div>
                      <div v-if="getFormulaDescription(item)" class="salary-item-desc">
                        {{ getFormulaDescription(item) }}
                      </div>
                    </div>
                    <div class="salary-item-amount deduction">¥{{ formatMoney(item.amount) }}</div>
                  </div>

                  <div v-if="item.inputs && item.inputs.length" class="salary-item-inputs">
                    <div v-for="input in item.inputs" :key="input.field_code" class="input-row">
                      <span class="input-label">
                        {{ getInputDisplayName(input.field_code) || input.field_code }}
                      </span>
                      <span v-if="isEmptyValue(input.value)" class="input-empty">未填写</span>
                      <span v-else class="input-value">¥{{ formatInputValue(input.value) }}</span>
                    </div>
                  </div>

                  <div v-if="item.formula" class="salary-item-formula-toggle" @click="toggleItem(item.item_code)">
                    <el-icon size="12">
                      <ArrowRight v-if="!isExpanded(item.item_code)" />
                      <ArrowDown v-else />
                    </el-icon>
                    <span>查看计算公式</span>
                  </div>
                  <div v-if="isExpanded(item.item_code) && item.formula" class="salary-item-formula-detail">
                    <div class="formula-line">
                      <span class="formula-label">原始公式</span>
                      <code>{{ item.formula }}</code>
                    </div>
                    <div v-if="item.inputs && item.inputs.length" class="formula-line">
                      <span class="formula-label">字段值</span>
                      <div class="formula-values">
                        <span v-for="input in item.inputs" :key="input.field_code" class="formula-value-tag">
                          {{ getInputDisplayName(input.field_code) || input.field_code }} =
                          {{ formatInputValue(input.value) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 最终结果 -->
              <div class="explain-section">
                <div class="section-header">
                  <el-icon :size="18" style="color:var(--primary)"><Document /></el-icon>
                  <span>最终结果</span>
                </div>

                <div v-for="item in groupedItems.total" :key="item.item_code" class="salary-item-card" :class="{ 'result-card': item.item_code === 'net_salary' }">
                  <div class="salary-item-header">
                    <div class="salary-item-info">
                      <div class="salary-item-name" :class="{ 'result-name': item.item_code === 'net_salary' }">
                        {{ item.item_name }}
                      </div>
                      <div v-if="getFormulaDescription(item)" class="salary-item-desc">
                        {{ getFormulaDescription(item) }}
                      </div>
                    </div>
                    <div class="salary-item-amount" :class="{ 'result-amount': item.item_code === 'net_salary' }">
                      ¥{{ formatMoney(item.amount) }}
                    </div>
                  </div>

                  <div v-if="item.inputs && item.inputs.length" class="salary-item-inputs">
                    <div v-for="input in item.inputs" :key="input.field_code" class="input-row">
                      <span class="input-label">
                        {{ getInputDisplayName(input.field_code) || input.field_code }}
                      </span>
                      <span v-if="isEmptyValue(input.value)" class="input-empty">未填写</span>
                      <span v-else class="input-value">¥{{ formatInputValue(input.value) }}</span>
                    </div>
                  </div>

                  <div v-if="item.formula" class="salary-item-formula-toggle" @click="toggleItem(item.item_code)">
                    <el-icon size="12">
                      <ArrowRight v-if="!isExpanded(item.item_code)" />
                      <ArrowDown v-else />
                    </el-icon>
                    <span>查看计算公式</span>
                  </div>
                  <div v-if="isExpanded(item.item_code) && item.formula" class="salary-item-formula-detail">
                    <div class="formula-line">
                      <span class="formula-label">原始公式</span>
                      <code>{{ item.formula }}</code>
                    </div>
                    <div v-if="item.inputs && item.inputs.length" class="formula-line">
                      <span class="formula-label">字段值</span>
                      <div class="formula-values">
                        <span v-for="input in item.inputs" :key="input.field_code" class="formula-value-tag">
                          {{ getInputDisplayName(input.field_code) || input.field_code }} =
                          {{ formatInputValue(input.value) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 异常提示 -->
              <div v-if="explainData.warnings && explainData.warnings.length" class="content-card" style="padding:16px">
                <div v-for="(w, i) in explainData.warnings" :key="i" style="display:flex; gap:8px; align-items:flex-start; margin-bottom:8px; font-size:13px; color:var(--warning)">
                  <el-icon :size="14" style="margin-top:2px"><WarningFilled /></el-icon>
                  <span>{{ w }}</span>
                </div>
              </div>
            </div>

            <!-- 右侧摘要栏 -->
            <div class="explain-sidebar">
              <div class="sidebar-card">
                <div class="sidebar-title">工资摘要</div>

                <div class="sidebar-row">
                  <span class="sidebar-label">应发合计</span>
                  <span class="sidebar-value">¥{{ summaryData?.grossSalary || '--' }}</span>
                </div>
                <div class="sidebar-divider" />
                <div class="sidebar-row">
                  <span class="sidebar-label">扣款合计</span>
                  <span class="sidebar-value deduction">¥{{ summaryData?.deductionTotal || '--' }}</span>
                </div>
                <div class="sidebar-divider" />
                <div class="sidebar-row sidebar-final">
                  <span class="sidebar-label">实发工资</span>
                  <span class="sidebar-final-value">¥{{ summaryData?.netSalary || '--' }}</span>
                </div>

                <div class="sidebar-divider" />

                <div class="sidebar-info">
                  <div class="sidebar-info-item">
                    <span class="sidebar-info-label">计算版本</span>
                    <span class="sidebar-info-value">v{{ summaryData?.calcVersion || '-' }}</span>
                  </div>
                  <div class="sidebar-info-item">
                    <span class="sidebar-info-label">员工</span>
                    <span class="sidebar-info-value">{{ selectedName }}</span>
                  </div>
                </div>

                <!-- 复制按钮 -->
                <el-button style="width:100%; margin-top:12px" @click="copyExplain">
                  <el-icon style="margin-right:4px"><CopyDocument /></el-icon>
                  复制解释
                </el-button>
              </div>
            </div>
          </div>
        </template>

        <!-- 空状态 -->
        <div v-else-if="!loading" class="content-card" style="text-align:center; padding:60px 20px">
          <el-icon :size="48" style="color:#D1D5DB; margin-bottom:12px"><Document /></el-icon>
          <p style="color:var(--text-tertiary); margin-bottom:16px">请先选择员工查看工资解释</p>
          <p v-if="employees.length === 0" style="color:var(--text-tertiary); font-size:13px">
            当前任务暂无员工数据，请先导入并完成工资计算
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 员工选择器栏 */
.employee-selector-bar {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 12px 20px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.emp-select-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.emp-nav {
  display: flex;
  align-items: center;
  gap: 2px;
}

.emp-nav-text {
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 48px;
  text-align: center;
}

/* 员工工资总览 */
.salary-overview {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 24px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.overview-left {
  flex: 0 0 auto;
  min-width: 140px;
}

.overview-emp-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.overview-emp-name {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.overview-emp-dept {
  font-size: 13px;
  color: var(--text-tertiary);
  background: #F3F4F6;
  padding: 2px 8px;
  border-radius: 4px;
}

.overview-center {
  flex: 1;
  text-align: center;
}

.overview-label {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.overview-amount {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary);
  line-height: 1.2;
}

.overview-right {
  flex: 0 0 auto;
  display: flex;
  gap: 24px;
}

.overview-stat-item {
  text-align: right;
}

.overview-stat-label {
  display: block;
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.overview-stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 两栏布局 */
.explain-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.explain-main {
  flex: 1;
  min-width: 0;
}

.explain-sidebar {
  width: 280px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
}

/* 分组标题 */
.explain-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* 工资项目卡片 */
.salary-item-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 10px;
}

.salary-item-card.result-card {
  border-color: var(--primary);
  background: var(--primary-light);
}

.salary-item-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.salary-item-info {
  flex: 1;
  min-width: 0;
}

.salary-item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.salary-item-name.result-name {
  font-size: 16px;
  color: var(--primary);
}

.salary-item-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.salary-item-amount {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.salary-item-amount.deduction {
  color: var(--danger);
}

.salary-item-amount.result-amount {
  font-size: 20px;
  color: var(--primary);
}

/* 输入值 */
.salary-item-inputs {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #F3F4F6;
}

.input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 0;
  font-size: 13px;
}

.input-label {
  color: var(--text-secondary);
}

.input-value {
  color: var(--text-primary);
  font-weight: 500;
}

.input-empty {
  color: var(--warning);
  font-weight: 500;
}

/* 公式折叠 */
.salary-item-formula-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
  cursor: pointer;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #F3F4F6;
  user-select: none;
}

.salary-item-formula-toggle:hover {
  color: var(--primary);
}

.salary-item-formula-detail {
  margin-top: 8px;
  padding: 10px 12px;
  background: #F9FAFB;
  border-radius: 6px;
  font-size: 13px;
}

.formula-line {
  margin-bottom: 6px;
}

.formula-line:last-child {
  margin-bottom: 0;
}

.formula-label {
  color: var(--text-tertiary);
  font-size: 12px;
  display: block;
  margin-bottom: 2px;
}

.formula-line code {
  font-size: 13px;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
  color: #6B7280;
  word-break: break-all;
}

.formula-values {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.formula-value-tag {
  background: #F3F4F6;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 警告 */
.salary-item-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--warning-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--warning);
}

/* 侧栏 */
.sidebar-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 20px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.sidebar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.sidebar-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.sidebar-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-value.deduction {
  color: var(--danger);
}

.sidebar-final {
  padding: 10px 0;
}

.sidebar-final-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--primary);
}

.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.sidebar-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.sidebar-info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-info-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.sidebar-info-value {
  font-size: 13px;
  color: var(--text-primary);
}
</style>
