<script setup lang="ts">
import { computed } from 'vue'
import type { RunStatusInfo } from '@/types'
import {
  getStatusConfig,
  canDelete,
  canVoid,
  canArchive,
  TONE_COLORS,
} from './payrollConfig'
import { formatDate, formatMonth, getStageIndex, PROCESS_STAGES } from '@/utils'

const props = defineProps<{
  runs: RunStatusInfo[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  keyword: string
  filterMonth: string
  filterStatus: string
  includeArchived: boolean
  operating: boolean
}>()

const emit = defineEmits<{
  (e: 'update:keyword', v: string): void
  (e: 'update:filterMonth', v: string): void
  (e: 'update:filterStatus', v: string): void
  (e: 'update:includeArchived', v: boolean): void
  (e: 'update:page', v: number): void
  (e: 'update:pageSize', v: number): void
  (e: 'search'): void
  (e: 'reset'): void
  (e: 'go-detail', row: RunStatusInfo): void
  (e: 'delete', row: RunStatusInfo): void
  (e: 'void', row: RunStatusInfo): void
  (e: 'archive', row: RunStatusInfo): void
}>()

function handleAction(row: RunStatusInfo, cmd: string) {
  if (cmd === 'detail') emit('go-detail', row)
  else if (cmd === 'delete') emit('delete', row)
  else if (cmd === 'void') emit('void', row)
  else if (cmd === 'archive') emit('archive', row)
}

function toneStyle(tone: string) {
  return TONE_COLORS[tone] || TONE_COLORS.neutral
}

function hasIssues(row: RunStatusInfo): boolean {
  return (row.block_count ?? 0) > 0 || (row.warn_count ?? 0) > 0
}

const statusOptions = computed(() => {
  const labels: Record<string, string> = {
    CREATED: '待导入',
    IMPORTED: '已导入',
    CHECK_FAILED: '检查未通过',
    CHECK_PASSED: '检查通过',
    CALCULATED: '已计算',
    CONFIRMED: '已确认',
    LOCKED: '已锁定',
    EXPORTED: '已导出',
    FAILED: '处理失败',
    VOIDED: '已作废',
  }
  return Object.entries(labels).map(([value, label]) => ({ value, label }))
})

const isEmpty = computed(() => !props.loading && props.runs.length === 0)
const isFiltered = computed(
  () => !!(props.keyword || props.filterMonth || props.filterStatus),
)
</script>

<template>
  <section class="hw-table-wrap">
    <!-- 工具栏 -->
    <div class="hw-toolbar">
      <div class="tb-left">
        <el-input
          :model-value="keyword"
          placeholder="搜索任务名称"
          clearable
          style="width: 200px"
          size="default"
          @update:model-value="(v: string) => emit('update:keyword', v)"
          @keyup.enter="emit('search')"
        />
        <el-date-picker
          :model-value="filterMonth"
          type="month"
          format="YYYY-MM"
          value-format="YYYY-MM"
          placeholder="工资月份"
          style="width: 136px"
          clearable
          size="default"
          @update:model-value="(v: string) => emit('update:filterMonth', v)"
        />
        <el-select
          :model-value="filterStatus"
          placeholder="全部状态"
          clearable
          style="width: 120px"
          size="default"
          @update:model-value="(v: string) => emit('update:filterStatus', v)"
        >
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-checkbox
          :model-value="includeArchived"
          class="tb-archived"
          @update:model-value="(v: boolean) => { emit('update:includeArchived', v); emit('search') }"
        >
          含已归档
        </el-checkbox>
      </div>
      <div class="tb-right">
        <span class="tb-total">共 <strong>{{ total }}</strong> 个任务</span>
        <el-button size="default" type="primary" @click="emit('search')">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button size="default" class="tb-reset-btn" @click="emit('reset')">
          <el-icon><Refresh /></el-icon>重置
        </el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      :data="runs"
      v-loading="loading"
      style="width: 100%"
      :header-cell-style="{
        background: '#F8FAFC',
        color: '#6B7280',
        fontWeight: 500,
        borderBottom: '1px solid #E5E7EB',
        fontSize: '13px',
        padding: '10px 12px',
      }"
      :cell-style="{
        borderBottom: '1px solid #F3F4F6',
        padding: '14px 12px',
      }"
      row-key="id"
      header-cell-class-name="hw-header-cell"
      @row-click="(row: RunStatusInfo) => emit('go-detail', row)"
    >
      <!-- 任务名称 -->
      <el-table-column label="任务名称" min-width="340">
        <template #default="{ row }">
          <div class="tc-name" @click.stop>
            <span class="tc-name-text" @click="emit('go-detail', row)">{{ row.name }}</span>
            <span class="tc-name-sub">创建于 {{ formatDate(row.created_at) }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- 工资月份 -->
      <el-table-column label="工资月份" width="110" align="center">
        <template #default="{ row }">
          <span class="tc-month">{{ formatMonth(row.payroll_month) }}</span>
        </template>
      </el-table-column>

      <!-- 核算进度 -->
      <el-table-column label="核算进度" width="150">
        <template #default="{ row }">
          <div class="tc-progress">
            <span
              class="tc-progress-label"
              :style="{ color: toneStyle(getStatusConfig(row.status).tone).text }"
            >
              <span
                class="tc-progress-dot"
                :style="{ background: toneStyle(getStatusConfig(row.status).tone).dot }"
              />
              {{ getStatusConfig(row.status).label }}
            </span>
            <span class="tc-progress-stage">
              {{ getStageIndex(row.status) + 1 }} / {{ PROCESS_STAGES.length }} · {{ PROCESS_STAGES[getStageIndex(row.status)]?.label }}
            </span>
          </div>
        </template>
      </el-table-column>

      <!-- 异常情况 -->
      <el-table-column label="异常情况" width="120">
        <template #default="{ row }">
          <div class="tc-issue">
            <template v-if="hasIssues(row)">
              <span v-if="(row.block_count ?? 0) > 0" class="tc-issue-block">
                阻断 {{ row.block_count }}
              </span>
              <span v-if="(row.warn_count ?? 0) > 0" class="tc-issue-warn">
                警告 {{ row.warn_count }}
              </span>
            </template>
            <span v-else class="tc-issue-ok">✓ 无异常</span>
          </div>
        </template>
      </el-table-column>

      <!-- 计算版本 -->
      <el-table-column label="计算版本" width="90" align="center">
        <template #default="{ row }">
          <span class="tc-ver">{{ row.current_calc_version > 0 ? `v${row.current_calc_version}` : '—' }}</span>
        </template>
      </el-table-column>

      <!-- 更新时间 -->
      <el-table-column label="更新时间" width="170" sortable>
        <template #default="{ row }">
          <span class="tc-time">{{ formatDate(row.updated_at) }}</span>
        </template>
      </el-table-column>

      <!-- 操作 -->
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <div class="tc-actions" @click.stop>
            <el-button
              class="tc-primary-action"
              size="small"
              @click="emit('go-detail', row)"
            >
              {{ getStatusConfig(row.status).action }}
              <el-icon style="margin-left: 2px"><ArrowRight /></el-icon>
            </el-button>
            <el-dropdown
              trigger="click"
              @command="(cmd: string) => handleAction(row, cmd)"
            >
              <el-button class="tc-more" size="small" title="更多操作">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="detail">
                    <el-icon size="14"><View /></el-icon>查看详情
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="canDelete(row.status)"
                    command="delete"
                    divided
                    class="danger-item"
                  >
                    <el-icon size="14"><Delete /></el-icon>删除任务
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="canVoid(row.status)"
                    command="void"
                    class="warn-item"
                  >
                    <el-icon size="14"><WarningFilled /></el-icon>作废任务
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="canArchive(row.status)"
                    command="archive"
                    divided
                  >
                    <el-icon size="14"><FolderOpened /></el-icon>归档任务
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>

      <!-- 空状态 -->
      <template #empty>
        <div v-if="isEmpty" class="tc-empty">
          <el-icon :size="44" class="tc-empty-icon"><FolderOpened /></el-icon>
          <p v-if="!isFiltered" class="tc-empty-title">暂无工资核算任务</p>
          <p v-else class="tc-empty-title">没有符合筛选条件的任务</p>
          <p v-if="!isFiltered" class="tc-empty-desc">点击下方按钮创建本月第一个核算任务</p>
          <el-button
            v-if="!isFiltered"
            type="primary"
            size="small"
            @click.stop="$router.push('/runs/create')"
          >
            <el-icon><Plus /></el-icon>新建核算任务
          </el-button>
          <el-button
            v-else
            size="small"
            @click.stop="emit('reset')"
          >
            <el-icon><Refresh /></el-icon>清空筛选
          </el-button>
        </div>
      </template>
    </el-table>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="hw-pagination">
      <el-pagination
        :model-value="page"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="sizes, prev, pager, next"
        background
        small
        @update:model-value="(v: number) => emit('update:page', v)"
        @update:page-size="(v: number) => emit('update:pageSize', v)"
        @current-change="(v: number) => { emit('update:page', v); emit('search') }"
        @size-change="(v: number) => { emit('update:pageSize', v); emit('search') }"
      />
    </div>
  </section>
</template>

<style scoped>
/* ===== 整体卡片 ===== */
.hw-table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: visible;
  margin-bottom: 24px;
}

/* ===== 工具栏 ===== */
.hw-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  min-height: 48px;
}

.tb-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tb-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.tb-total {
  font-size: 13px;
  color: var(--text-tertiary);
  white-space: nowrap;
  margin-right: 4px;
}

.tb-total strong {
  color: var(--text-primary);
  font-weight: 600;
}

.tb-archived {
  margin-left: 2px;
}

.tb-archived :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-tertiary);
}

.tb-reset-btn {
  --el-button-text-color: var(--text-secondary);
}

/* ===== 表格表头禁止断行 ===== */
:deep(.hw-header-cell .cell) {
  word-break: keep-all !important;
  white-space: nowrap !important;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 表格单元格禁止断行保护 ===== */
:deep(.el-table__body .el-table__cell > .cell) {
  word-break: keep-all;
  overflow: visible;
}

/* ===== 任务名称列 ===== */
.tc-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.3;
  cursor: pointer;
}

.tc-name-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  transition: color 0.12s;
}

.tc-name-text:hover {
  color: #2563EB;
}

.tc-name-sub {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ===== 工资月份 ===== */
.tc-month {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
  white-space: nowrap;
}

/* ===== 核算进度列 ===== */
.tc-progress {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tc-progress-label {
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.tc-progress-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tc-progress-stage {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.2;
  white-space: nowrap;
}

/* ===== 异常情况列 ===== */
.tc-issue {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.3;
}

.tc-issue-ok {
  font-size: 13px;
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tc-issue-block {
  font-size: 13px;
  font-weight: 500;
  color: #DC2626;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tc-issue-block::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #DC2626;
  flex-shrink: 0;
}

.tc-issue-warn {
  font-size: 13px;
  font-weight: 500;
  color: #D97706;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tc-issue-warn::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #D97706;
  flex-shrink: 0;
}

/* ===== 版本 & 时间 ===== */
.tc-ver {
  font-size: 13px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.tc-time {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* ===== 操作列 ===== */
.tc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.tc-primary-action {
  font-size: 13px;
  padding: 5px 12px;
  border-radius: 6px;
  --el-button-bg-color: #F3F4F6;
  --el-button-border-color: #E5E7EB;
  --el-button-text-color: var(--text-primary);
  --el-button-hover-bg-color: #EFF6FF;
  --el-button-hover-border-color: #2563EB;
  --el-button-hover-text-color: #2563EB;
  transition: all 0.12s;
  flex-shrink: 0;
}

.tc-primary-action:hover {
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.1);
}

.tc-more {
  padding: 4px 10px;
  border-radius: 6px;
  min-width: 32px;
  height: 30px;
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-text-color: #9CA3AF;
  --el-button-hover-bg-color: #F3F4F6;
  --el-button-hover-border-color: #E5E7EB;
  --el-button-hover-text-color: var(--text-primary);
  flex-shrink: 0;
}

/* ===== 空状态 ===== */
.tc-empty {
  padding: 40px 0;
  text-align: center;
}

.tc-empty-icon {
  color: #D1D5DB;
  margin-bottom: 8px;
}

.tc-empty-title {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 4px;
}

.tc-empty-desc {
  color: var(--text-tertiary);
  font-size: 13px;
  margin-bottom: 12px;
}

/* ===== 分页 ===== */
.hw-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 10px 20px;
  border-top: 1px solid var(--border);
}

/* ===== 下拉菜单危险项 ===== */
:deep(.danger-item) {
  color: #DC2626 !important;
}

:deep(.danger-item:hover) {
  background: #FEF2F2 !important;
}

:deep(.warn-item) {
  color: #D97706 !important;
}

:deep(.warn-item:hover) {
  background: #FFFBEB !important;
}
</style>
