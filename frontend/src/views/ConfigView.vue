<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <div class="page-breadcrumb" style="padding-top:24px">
        <a href="javascript:;" @click="router.push('/')">工资核算任务</a>
        <span class="sep">/</span>
        <span>系统配置</span>
      </div>

      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">系统配置</h1>
          <p class="page-subtitle">查看系统字段、公式和检查规则配置</p>
        </div>
      </div>

      <el-card>
        <el-empty description="配置中心（后续版本支持页面管理）" />
        <p style="text-align:center; color:var(--text-tertiary)">MVP 阶段配置文件位于项目 config/ 目录</p>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
</style>
