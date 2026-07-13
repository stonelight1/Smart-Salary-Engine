<script setup lang="ts">
import { computed } from 'vue'
import { PROCESS_STAGES } from './payrollConfig'
import type { RunStatusInfo } from '@/types'

const props = defineProps<{
  processCounts: number[]
  activeStage: number
  blockTasks: number
  warnTasks: number
  total: number
  runs: RunStatusInfo[]
}>()

const emit = defineEmits<{
  (e: 'stage-select', idx: number): void
  (e: 'view-abnormal'): void
}>()

/** 某阶段是否有异常（仅 check 阶段） */
function stageHasError(idx: number): boolean {
  if (idx !== 1) return false
  return props.runs.some((r) => {
    const stages: Record<string, number> = {
      CREATED: 0, IMPORTING: 0, IMPORTED: 0,
      CHECKING: 1, CHECK_FAILED: 1, CHECK_PASSED: 1,
      CALCULATING: 2, CALCULATED: 2,
      CONFIRMED: 3,
      EXPORTED: 4,
      LOCKED: 5, FAILED: 5, VOIDED: 5,
    }
    return stages[r.status] === idx && r.status === 'CHECK_FAILED'
  })
}

const hasIssues = computed(() => props.blockTasks > 0 || props.warnTasks > 0)
</script>

<template>
  <section class="hw-process-wrap">
    <!-- 流程导航 -->
    <div class="hw-process">
      <div
        v-for="(stage, idx) in PROCESS_STAGES"
        :key="stage.key"
        class="process-segment"
        :class="{
          'is-active': activeStage === idx,
          'is-zero': processCounts[idx] === 0,
          'has-count': processCounts[idx] > 0,
          'is-error': stageHasError(idx),
        }"
        :title="`筛选 ${stage.label} 阶段任务`"
        @click="emit('stage-select', idx)"
      >
        <span class="ps-label">{{ stage.label }}</span>
        <span class="ps-count" :class="{ 'is-zero-count': processCounts[idx] === 0 }">{{ processCounts[idx] }}</span>
        <span v-if="idx < PROCESS_STAGES.length - 1" class="ps-sep" />
      </div>
    </div>

    <!-- 状态摘要 -->
    <div v-if="total > 0" class="hw-summary" :class="{ 'summary-issue': hasIssues }">
      <template v-if="hasIssues">
        <span class="si-item si-block" v-if="blockTasks > 0">
          <span class="si-dot" />{{ blockTasks }} 个阻断任务
        </span>
        <span class="si-sep" v-if="blockTasks > 0 && warnTasks > 0">·</span>
        <span class="si-item si-warn" v-if="warnTasks > 0">
          <span class="si-dot" />{{ warnTasks }} 个警告任务
        </span>
        <span class="si-action" @click="emit('view-abnormal')">
          查看异常任务
          <el-icon size="12"><ArrowRight /></el-icon>
        </span>
      </template>
      <template v-else>
        <span class="si-item si-ok">
          <span class="si-dot" />当前无待处理异常，所有核算任务运行正常
        </span>
      </template>
    </div>
  </section>
</template>

<style scoped>
.hw-process-wrap {
  margin-bottom: 14px;
}

/* ===== 流程导航 (分段式) ===== */
.hw-process {
  display: flex;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  height: 46px;
}

.process-segment {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  position: relative;
  transition: background 0.12s, color 0.12s;
  padding: 0 10px;
  user-select: none;
}

.process-segment:hover {
  background: #F8FAFC;
}

.process-segment.is-active {
  background: #EFF6FF;
}

.process-segment.is-error {
  background: #FFF5F5;
}

.process-segment.is-error.is-active {
  background: #FEF2F2;
}

.ps-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  transition: color 0.12s;
}

.is-zero .ps-label {
  color: var(--text-tertiary);
  font-weight: 400;
}

.is-active .ps-label {
  color: #2563EB;
  font-weight: 600;
}

.is-error .ps-label {
  color: #DC2626;
}

.ps-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  background: #F3F4F6;
  padding: 0 5px;
  border-radius: 4px;
  line-height: 18px;
  min-width: 18px;
  text-align: center;
  transition: all 0.12s;
}

.ps-count.is-zero-count {
  color: var(--text-tertiary);
  background: transparent;
  padding: 0;
  min-width: auto;
  font-weight: 400;
}

.is-active .ps-count:not(.is-zero-count) {
  background: #DBEAFE;
  color: #2563EB;
}

.is-error .ps-count:not(.is-zero-count) {
  background: #FEE2E2;
  color: #DC2626;
}

.ps-sep {
  position: absolute;
  right: 0;
  top: 12px;
  bottom: 12px;
  width: 1px;
  background: var(--border);
}

/* ===== 状态摘要 ===== */
.hw-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  margin-top: 8px;
  border-radius: 8px;
  background: #F0FDF4;
  min-height: 32px;
  font-size: 13px;
}

.hw-summary.summary-issue {
  background: #FFF5F5;
}

.si-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
}

.si-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.si-ok .si-dot {
  background: #16A34A;
}

.si-block .si-dot {
  background: #DC2626;
}

.si-block {
  color: #DC2626;
  font-weight: 500;
}

.si-warn .si-dot {
  background: #D97706;
}

.si-warn {
  color: #D97706;
  font-weight: 500;
}

.si-sep {
  color: var(--border);
  font-weight: 300;
}

.si-action {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #DC2626;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.12s;
}

.si-action:hover {
  opacity: 0.75;
}

@media (max-width: 900px) {
  .hw-process {
    overflow-x: auto;
  }
  .process-segment {
    min-width: 120px;
    flex: none;
  }
}
</style>
