<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { calcApi, runApi } from '@/api'
import { formatMoney } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const calculating = ref(false)
const calculated = ref(false)
const calcResult = ref<any>(null)
const results = ref<any[]>([])
const run = ref<any>(null)
const loading = ref(false)

onMounted(loadRun)

async function loadRun() {
  loading.value = true
  try {
    const res = await runApi.get(runId)
    run.value = res.data.data
    if (run.value.current_calc_version > 0) {
      calculated.value = true
      loadResults()
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function loadResults() {
  try {
    const res = await calcApi.getResults(runId)
    results.value = res.data.data.items || []
  } catch {
    // ignore
  }
}

async function startCalculate() {
  calculating.value = true
  try {
    const res = await calcApi.run(runId)
    calcResult.value = res.data.data
    calculated.value = true
    ElMessage.success(`计算完成！成功: ${calcResult.value.success_count}, 失败: ${calcResult.value.failed_count}`)
    loadResults()
    loadRun()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '计算失败')
  } finally {
    calculating.value = false
  }
}

const totalSalary = computed(() => {
  const total = results.value.reduce((s, r) => s + parseFloat(r.net_salary || '0'), 0)
  return formatMoney(total)
})
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
        <span>工资计算</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">工资计算</h1>
          <p class="page-subtitle">基于公式配置执行工资核算</p>
        </div>
      </div>

      <div class="content-card">
        <el-steps :active="calculated ? 2 : 1" simple>
          <el-step title="① 数据检查" />
          <el-step title="② 工资计算" />
          <el-step title="③ 工资解释" />
        </el-steps>

        <div style="margin-top:20px; display:flex; align-items:center; gap:16px">
          <el-button type="primary" size="large" :loading="calculating" :disabled="calculating" @click="startCalculate">
            {{ calculating ? '计算中...' : calculated ? '重新计算' : '开始工资计算' }}
          </el-button>
          <el-tag v-if="run" type="info" effect="plain">当前版本: v{{ run.current_calc_version || '-' }}</el-tag>
        </div>
      </div>

      <div v-if="calculated" class="content-card" style="margin-top:16px">
        <div class="content-card-header">
          <div class="content-card-title">
            计算结果
            <el-tag style="margin-left:8px" type="success" effect="plain" size="small">{{ results.length }} 名员工</el-tag>
            <el-tag style="margin-left:8px" effect="plain" size="small">实发合计: ¥{{ totalSalary }}</el-tag>
          </div>
        </div>
        <el-table :data="results" stripe>
          <el-table-column prop="employee_name" label="员工" width="120" />
          <el-table-column prop="gross_salary" label="应发工资" width="140">
            <template #default="{ row }">{{ row.gross_salary ? formatMoney(row.gross_salary) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="deduction_total" label="扣款合计" width="140">
            <template #default="{ row }">{{ row.deduction_total ? formatMoney(row.deduction_total) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="net_salary" label="实发工资" width="140">
            <template #default="{ row }">
              <strong>{{ row.net_salary ? formatMoney(row.net_salary) : '-' }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="router.push(`/runs/${runId}/explain?emp=${row.employee_ref_id}`)">
                查看解释
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
