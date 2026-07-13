<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { employeeApi } from '@/api'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const employees = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const total = ref(0)

onMounted(() => fetchEmployees())

async function fetchEmployees() {
  loading.value = true
  try {
    const res = await employeeApi.list(runId, { keyword: keyword.value || undefined })
    employees.value = res.data.data.items || []
    total.value = res.data.data.total || 0
  } catch {
    ElMessage.error('获取员工列表失败')
  } finally {
    loading.value = false
  }
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
        <span>员工数据池</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">员工数据池</h1>
          <p class="page-subtitle">查看和管理所有导入的员工工资数据</p>
        </div>
      </div>

      <div class="content-card">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px">
          <el-input v-model="keyword" placeholder="搜索员工姓名" clearable style="width:280px" @keyup.enter="fetchEmployees" />
          <el-button @click="fetchEmployees"><el-icon><Search /></el-icon>搜索</el-button>
          <span style="color:var(--text-tertiary); font-size:13px">共 {{ total }} 名员工</span>
        </div>

        <el-table :data="employees" v-loading="loading" stripe>
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="employee_name" label="员工姓名" width="140" />
          <el-table-column label="基本工资" width="130">
            <template #default="{ row }">{{ row.fields?.base_salary || '-' }}</template>
          </el-table-column>
          <el-table-column label="绩效奖金" width="130">
            <template #default="{ row }">{{ row.fields?.performance_bonus || '-' }}</template>
          </el-table-column>
          <el-table-column label="补贴合计" width="130">
            <template #default="{ row }">{{ row.fields?.meal_allowance || '-' }}</template>
          </el-table-column>
          <el-table-column label="扣款" width="130">
            <template #default="{ row }">{{ row.fields?.other_deduction || '-' }}</template>
          </el-table-column>
          <el-table-column label="出勤天数" width="120">
            <template #default="{ row }">{{ row.fields?.attendance_days || '-' }}</template>
          </el-table-column>
          <el-table-column prop="issue_count" label="异常数" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'NORMAL' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
