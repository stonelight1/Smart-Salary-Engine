<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkApi } from '@/api'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const checking = ref(false)
const checked = ref(false)
const checkResult = ref<{ block_count: number; warn_count: number; info_count: number } | null>(null)

const canCalculate = computed(() => {
  return checked.value && (checkResult.value?.block_count ?? 0) === 0
})

async function runCheck() {
  checking.value = true
  try {
    const res = await checkApi.run(runId)
    const data = res.data.data
    checkResult.value = { block_count: data.block_count, warn_count: data.warn_count, info_count: data.info_count }
    checked.value = true
    if (data.block_count > 0) {
      ElMessage.warning(`发现 ${data.block_count} 个严重异常，请处理后再计算`)
    } else {
      ElMessage.success('检查通过！可以进行工资计算')
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '检查失败')
  } finally {
    checking.value = false
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
        <span>数据检查</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">数据检查</h1>
          <p class="page-subtitle">检查员工数据的完整性、格式和逻辑正确性</p>
        </div>
      </div>

      <!-- 概要卡片 -->
      <div class="stat-cards">
        <div class="stat-card" style="height:80px">
          <div class="stat-card-icon" style="background:#EFF6FF; color:var(--primary);" :class="checkResult?.block_count && checkResult.block_count > 0 ? 'orange' : ''">
            <el-icon :size="20"><WarningFilled /></el-icon>
          </div>
          <div class="stat-card-body">
            <div class="stat-card-value" :style="{ color: (checkResult?.block_count ?? 0) > 0 ? 'var(--danger)' : 'var(--text-primary)' }">
              {{ checkResult?.block_count ?? '-' }}
            </div>
            <div class="stat-card-label">阻断</div>
          </div>
        </div>
        <div class="stat-card" style="height:80px">
          <div class="stat-card-icon" style="background:#FFFBEB; color:var(--warning)">
            <el-icon :size="20"><Warning /></el-icon>
          </div>
          <div class="stat-card-body">
            <div class="stat-card-value" :style="{ color: (checkResult?.warn_count ?? 0) > 0 ? 'var(--warning)' : 'var(--text-primary)' }">
              {{ checkResult?.warn_count ?? '-' }}
            </div>
            <div class="stat-card-label">警告</div>
          </div>
        </div>
        <div class="stat-card" style="height:80px">
          <div class="stat-card-icon" style="background:#F3F4F6; color:var(--info)">
            <el-icon :size="20"><InfoFilled /></el-icon>
          </div>
          <div class="stat-card-body">
            <div class="stat-card-value">{{ checkResult?.info_count ?? '-' }}</div>
            <div class="stat-card-label">提示</div>
          </div>
        </div>
        <div class="stat-card" style="height:80px">
          <div class="stat-card-icon" :style="{ background: canCalculate ? '#F0FDF4' : '#FEF2F2', color: canCalculate ? 'var(--success)' : 'var(--danger)' }">
            <el-icon :size="20"><CircleCheck /></el-icon>
          </div>
          <div class="stat-card-body">
            <div class="stat-card-value" :style="{ color: canCalculate ? 'var(--success)' : 'var(--danger)' }">
              {{ canCalculate ? '是' : checkResult ? '否' : '-' }}
            </div>
            <div class="stat-card-label">可否计算</div>
          </div>
        </div>
      </div>

      <!-- 操作 -->
      <div class="content-card">
        <div style="display:flex; align-items:center; gap:12px">
          <el-button type="primary" size="large" :loading="checking" @click="runCheck">
            <el-icon><Select /></el-icon>{{ checking ? '检查中...' : checked ? '重新检查' : '发起检查' }}
          </el-button>
          <el-button v-if="checked" @click="router.push(`/runs/${runId}/issues`)"><el-icon><WarningFilled /></el-icon>查看异常详情</el-button>
          <el-button v-if="canCalculate" type="success" @click="router.push(`/runs/${runId}/calculate`)">
            工资计算<el-icon style="margin-left:4px"><ArrowRight /></el-icon>
          </el-button>
        </div>
        <p v-if="!checked" style="color:var(--text-tertiary); font-size:13px; margin-top:12px">
          点击「发起检查」系统将自动检查数据完整性、格式合法性、逻辑正确性。
        </p>
        <p v-if="checked && (checkResult?.block_count ?? 0) > 0" style="color:var(--danger); font-size:13px; margin-top:12px">
          存在 {{ checkResult?.block_count }} 个阻断异常，请前往异常中心处理后重新检查。
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
