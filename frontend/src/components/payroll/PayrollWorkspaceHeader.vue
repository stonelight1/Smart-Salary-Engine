<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <header class="hw-header">
    <div class="hw-header-left">
      <h1 class="hw-title">工资核算工作台</h1>
      <p class="hw-desc">统一管理每月工资数据导入、计算、检查、审核与导出</p>
    </div>
    <el-button type="primary" size="large" class="hw-create-btn" @click="router.push('/runs/create')">
      <el-icon><Plus /></el-icon>
      <span>新建核算任务</span>
    </el-button>
  </header>
</template>

<style scoped>
.hw-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 0 14px;
}

.hw-header-left {
  flex: 1;
  min-width: 0;
}

.hw-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  margin: 0 0 3px;
  letter-spacing: -0.01em;
}

.hw-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.hw-create-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
}

.hw-create-btn .el-icon {
  font-size: 16px;
  margin-right: 3px;
}

@media (max-width: 1100px) {
  .hw-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
