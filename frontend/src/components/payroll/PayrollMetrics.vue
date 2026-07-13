<script setup lang="ts">
defineProps<{
  total: number
  processing: number
  abnormal: number
  completed: number
  activeFilter: string | null
  activeStage: number
}>()

const emit = defineEmits<{
  (e: 'filter-change', type: string | null): void
}>()
</script>

<template>
  <section class="hw-metrics">
    <!-- 全部任务 -->
    <div
      class="metric-card"
      :class="{ 'is-selected': activeFilter === null && activeStage < 0 }"
      @click="emit('filter-change', null)"
    >
      <div class="mc-content">
        <span class="mc-label">全部任务</span>
        <span class="mc-value">{{ total }}</span>
      </div>
      <div class="mc-accent" />
    </div>

    <!-- 进行中 -->
    <div
      class="metric-card"
      :class="{ 'is-selected': activeFilter === 'processing' }"
      @click="emit('filter-change', activeFilter === 'processing' ? null : 'processing')"
    >
      <div class="mc-content">
        <span class="mc-label">进行中</span>
        <span class="mc-value mc-value-processing">{{ processing }}</span>
      </div>
      <div class="mc-accent" />
    </div>

    <!-- 存在异常 -->
    <div
      class="metric-card"
      :class="{
        'is-selected': activeFilter === 'abnormal',
        'has-issue': abnormal > 0,
      }"
      @click="emit('filter-change', activeFilter === 'abnormal' ? null : 'abnormal')"
    >
      <div class="mc-content">
        <span class="mc-label">
          <span v-if="abnormal > 0" class="mc-dot mc-dot-danger" />
          存在异常
        </span>
        <span class="mc-value" :class="{ 'mc-value-danger': abnormal > 0, 'mc-value-zero': abnormal === 0 }">{{ abnormal }}</span>
      </div>
      <div class="mc-accent" />
    </div>

    <!-- 已完成 -->
    <div
      class="metric-card"
      :class="{ 'is-selected': activeFilter === 'completed' }"
      @click="emit('filter-change', activeFilter === 'completed' ? null : 'completed')"
    >
      <div class="mc-content">
        <span class="mc-label">已完成</span>
        <span class="mc-value mc-value-completed">{{ completed }}</span>
      </div>
      <div class="mc-accent" />
    </div>
  </section>
</template>

<style scoped>
.hw-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.metric-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  overflow: hidden;
  height: 64px;
  display: flex;
  align-items: center;
}

.metric-card:hover {
  border-color: #D1D5DB;
  background: #FAFBFC;
}

.metric-card.is-selected {
  border-color: #2563EB;
  background: #F8FAFF;
}

.metric-card.has-issue {
  border-color: #FCA5A5;
}

.metric-card.has-issue.is-selected {
  border-color: #DC2626;
  background: #FFF5F5;
}

.mc-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: transparent;
  transition: background 0.15s;
}

.is-selected .mc-accent {
  background: #2563EB;
}

.has-issue.is-selected .mc-accent {
  background: #DC2626;
}

.mc-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
}

.mc-label {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 5px;
}

.mc-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mc-dot-danger {
  background: #DC2626;
}

.mc-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  transition: color 0.15s;
}

.mc-value-processing {
  color: #2563EB;
}

.mc-value-completed {
  color: #16A34A;
}

.mc-value-danger {
  color: #DC2626;
}

.mc-value-zero {
  color: var(--text-tertiary);
}

@media (max-width: 1100px) {
  .hw-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
