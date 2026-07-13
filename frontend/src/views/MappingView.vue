<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string
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
        <span>识别确认</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">识别确认</h1>
          <p class="page-subtitle">确认 Sheet 类型和列映射是否正确</p>
        </div>
      </div>

      <div class="content-card">
        <el-steps :active="1" simple style="margin-bottom:20px">
          <el-step title="① 导入 Excel" />
          <el-step title="② 确认识别结果" />
          <el-step title="③ 数据检查" />
        </el-steps>
        <el-empty description="请先导入 Excel 文件" />
        <div style="margin-top:12px; display:flex; gap:12px">
          <el-button @click="router.push(`/runs/${runId}/import`)"><el-icon><Upload /></el-icon>前往导入</el-button>
          <el-button type="primary" @click="router.push(`/runs/${runId}/check`)">进入检查<el-icon style="margin-left:4px"><ArrowRight /></el-icon></el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
