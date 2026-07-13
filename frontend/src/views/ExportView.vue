<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { exportApi, runApi } from '@/api'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const exporting = ref(false)
const exportResult = ref<any>(null)
const run = ref<any>(null)
const loading = ref(false)

const includeTrace = ref(true)
const includeIssues = ref(true)
const includeSources = ref(true)

onMounted(async () => {
  loading.value = true
  try {
    const res = await runApi.get(runId)
    run.value = res.data.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})

async function startExport() {
  exporting.value = true
  try {
    const res = await exportApi.run(runId, {
      calc_version: run.value?.current_calc_version || 1,
      include_trace: includeTrace.value,
      include_issues: includeIssues.value,
      include_sources: includeSources.value,
    })
    exportResult.value = res.data.data
    ElMessage.success('导出成功！')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

function download() {
  if (exportResult.value) {
    window.open(exportResult.value.download_url, '_blank')
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
        <span>导出中心</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">导出中心</h1>
          <p class="page-subtitle">导出工资核算结果到 Excel 文件</p>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :span="14">
          <el-card>
            <template #header>
              <span style="font-weight:600">导出选项</span>
            </template>

            <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
              导出以工资主表为模板生成新 Excel 文件，原始文件不会被修改。
            </el-alert>

            <div style="margin-bottom:16px">
              <el-checkbox v-model="includeTrace" label="包含计算过程" border />
            </div>
            <div style="margin-bottom:16px">
              <el-checkbox v-model="includeIssues" label="包含异常报告" border />
            </div>
            <div style="margin-bottom:16px">
              <el-checkbox v-model="includeSources" label="包含字段来源" border />
            </div>

            <el-button type="primary" size="large" :loading="exporting" @click="startExport">
              <el-icon v-if="!exporting"><Download /></el-icon>{{ exporting ? '导出中...' : '开始导出' }}
            </el-button>

            <el-button v-if="exportResult" type="success" size="large" style="margin-left:12px" @click="download">
              <el-icon><Download /></el-icon>下载文件
            </el-button>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card>
            <template #header>
              <span style="font-weight:600">导出记录</span>
            </template>
            <div v-if="exportResult">
              <div style="margin-bottom:8px">
                <span style="color:var(--text-tertiary)">文件名：</span>
                <div style="word-break:break-all; font-size:13px">{{ exportResult.file_name }}</div>
              </div>
              <el-button type="primary" link @click="download">下载</el-button>
            </div>
            <el-empty v-else description="尚未导出" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
</style>
