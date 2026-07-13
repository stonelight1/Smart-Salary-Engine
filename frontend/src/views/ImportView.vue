<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { importApi } from '@/api'
import { formatDate } from '@/utils'

const route = useRoute()
const router = useRouter()
const runId = route.params.runId as string

const files = ref<any[]>([])
const uploading = ref<string | null>(null)
const repairing = ref<string | null>(null)   // 正在修复的 role
const repairMsg = ref('')                     // 修复状态消息
const loading = ref(false)

// 错误码 → 中文提示映射
const ERROR_MESSAGES: Record<string, string> = {
  EXCEL_EMPTY_FILE: '上传文件为空，请选择有效的 Excel 文件。',
  EXCEL_TOO_LARGE: '文件大小超过 50MB 限制。',
  EXCEL_INVALID_EXTENSION: '只支持 .xlsx 格式文件。',
  EXCEL_INVALID_FORMAT: '文件格式不正确。该文件虽然使用了 .xlsx 后缀，但不是有效的 Excel 工作簿，请使用 Excel 重新另存为 .xlsx 后上传。',
  EXCEL_CORRUPTED_ZIP: '文件损坏或不是有效的 Excel 文件，请使用 Excel 打开并另存为 .xlsx 后重新上传。',
  EXCEL_INVALID_STRUCTURE: 'Excel 文件内部结构不完整，请使用 Excel 重新打开并另存为 .xlsx 后上传。',
  EXCEL_REPAIR_TIMEOUT: 'Excel 自动修复超时，请使用 Excel 打开并另存为 .xlsx 后重新上传。',
  EXCEL_REPAIR_FAILED: 'Excel 文件内部结构异常，系统自动修复未成功。请使用 Microsoft Excel 打开文件，选择「另存为」Excel 工作簿（.xlsx）后重新上传。',
}

/** 根据错误响应获取用户可读的提示 */
function getUserErrorMessage(err: any): string {
  const errorCode = err.response?.data?.error_code
  const serverMsg = err.response?.data?.message

  // 优先使用错误码映射
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }

  // 有服务器返回消息且不包含敏感内容
  if (serverMsg && typeof serverMsg === 'string') {
    // 过滤掉可能的文件路径
    if (serverMsg.includes('/') || serverMsg.includes('\\')) {
      return '文件处理失败，请稍后重试。'
    }
    return serverMsg
  }

  return '导入失败，请稍后重试。'
}

// 数据来源卡片定义
const DATA_SOURCES = [
  {
    key: 'MAIN',
    title: '员工基础薪资',
    desc: '导入员工档案或工资主表，含基本工资、岗位、部门等基础信息',
    icon: 'UserFilled',
    color: '#2563EB',
    bg: '#EFF6FF',
  },
  {
    key: 'ATTENDANCE',
    title: '考勤数据',
    desc: '导入考勤表，含应出勤天数、核薪天数、加班时长等',
    icon: 'Calendar',
    color: '#7C3AED',
    bg: '#F3E8FF',
  },
  {
    key: 'PERFORMANCE',
    title: '绩效数据',
    desc: '导入绩效系数或最终绩效金额',
    icon: 'TrendCharts',
    color: '#D97706',
    bg: '#FFFBEB',
  },
  {
    key: 'COMMISSION',
    title: '提成数据',
    desc: '导入视播提成、客服提成、销售提成等最终金额',
    icon: 'Money',
    color: '#059669',
    bg: '#F0FDF4',
  },
  {
    key: 'SOCIAL_SECURITY',
    title: '社保公积金',
    desc: '导入社保公积金扣缴表，含个人与公司承担部分',
    icon: 'Shield',
    color: '#0891B2',
    bg: '#ECFEFF',
  },
  {
    key: 'ADJUSTMENT',
    title: '其他调整项',
    desc: '导入加班费、补贴、补发、扣款等调整数据',
    icon: 'EditPen',
    color: '#DC2626',
    bg: '#FEF2F2',
  },
]

onMounted(() => {
  loadFiles()
})

async function loadFiles() {
  loading.value = true
  try {
    const res = await importApi.getFiles(runId)
    files.value = res.data.data.items || []
  } catch {
    // 新接口可能尚未部署，静默处理
    files.value = []
  } finally {
    loading.value = false
  }
}

// 按 role 分组文件
const fileGroups = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const src of DATA_SOURCES) {
    groups[src.key] = []
  }
  for (const f of files.value) {
    const key = f.file_role
    if (!groups[key]) groups[key] = []
    groups[key].push(f)
  }
  return groups
})

function getLatestFile(role: string): any | null {
  const list = fileGroups.value[role] || []
  return list.length > 0 ? list[0] : null
}

function canUpload(role: string): boolean {
  // MAIN 必须第一个上传，其他角色在 MAIN 之后
  if (role === 'MAIN') return true
  return fileGroups.value['MAIN'] && fileGroups.value['MAIN'].length > 0
}

async function handleUpload(role: string) {
  if (!canUpload(role)) {
    ElMessage.warning('请先上传员工基础薪资数据')
    return
  }
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls,.csv'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['xlsx', 'xls', 'csv'].includes(ext || '')) {
      ElMessage.warning('只支持 .xlsx、.xls、.csv 格式')
      return
    }
    uploading.value = role
    repairMsg.value = ''
    try {
      const res = await importApi.upload(runId, file, role)
      const data = res.data.data
      const respMsg = res.data.message

      // 检查是否进行了自动修复
      if (data.repaired) {
        if (data.repair_method === 'VALUE_ONLY_REBUILD') {
          ElMessage.warning({
            message: '文件已通过兼容模式读取。部分公式、样式、图片或批注可能未保留，请确认导入数据无误后继续。',
            duration: 6000,
          })
        } else {
          ElMessage.success('文件已自动修复并成功读取。系统未修改原始 Excel。')
        }
      } else {
        ElMessage.success(`${getDataSourceTitle(role)} 导入成功`)
      }

      // 显示数据行统计（排除汇总行和空白行）
      const pool = data.data_pool
      if (pool && (pool.employee_row_count != null)) {
        const parts: string[] = [`识别到员工数据 ${pool.employee_row_count} 条`]
        if (pool.summary_row_count > 0) parts.push(`自动忽略汇总行 ${pool.summary_row_count} 条`)
        if (pool.empty_row_count > 0) parts.push(`自动忽略空白行 ${pool.empty_row_count} 条`)
        if (pool.invalid_row_count > 0) parts.push(`疑似异常行 ${pool.invalid_row_count} 条`)
        ElMessage.info(parts.join('，'))
      }

      if (data.need_confirm_count > 0) {
        ElMessage.info(`有 ${data.need_confirm_count} 项映射需要确认`)
      }
      // 刷新文件列表
      await loadFiles()
    } catch (err: any) {
      const msg = getUserErrorMessage(err)
      // 如果是修复失败且有错误码，不弹默认错误
      const errorCode = err.response?.data?.error_code
      if (errorCode === 'EXCEL_REPAIR_FAILED') {
        ElMessageBox.alert(msg, '文件解析失败', {
          confirmButtonText: '知道了',
          type: 'warning',
        })
      } else {
        ElMessage.error(msg)
      }
    } finally {
      uploading.value = null
    }
  }
  input.click()
}

function getDataSourceTitle(role: string): string {
  return DATA_SOURCES.find((s) => s.key === role)?.title || role
}

function formatFileSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function goToMapping(role: string) {
  const file = getLatestFile(role)
  if (file) {
    router.push(`/runs/${runId}/mapping?batch=${file.batch_id}`)
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
        <span>数据准备</span>
      </div>

      <!-- 页面标题 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">数据准备</h1>
          <p class="page-subtitle">上传并整理工资核算所需的各项数据</p>
        </div>
        <el-button v-if="files.length > 0" type="primary" @click="router.push(`/runs/${runId}/data-summary`)">
          查看数据汇总
        </el-button>
      </div>

      <!-- 数据来源卡片网格 -->
      <div class="data-source-grid">
        <div
          v-for="src in DATA_SOURCES"
          :key="src.key"
          class="data-source-card"
          :class="{ 'card-disabled': !canUpload(src.key) && src.key !== 'MAIN' }"
        >
          <!-- 卡片头部 -->
          <div class="ds-header">
            <div class="ds-icon" :style="{ background: src.bg, color: src.color }">
              <el-icon :size="20">
                <component :is="src.icon" />
              </el-icon>
            </div>
            <div class="ds-title-group">
              <span class="ds-title">{{ src.title }}</span>
              <span v-if="!canUpload(src.key) && src.key !== 'MAIN'" class="ds-hint">需先上传基础薪资</span>
            </div>
          </div>

          <!-- 已导入信息 -->
          <div v-if="getLatestFile(src.key)" class="ds-file-info">
            <div class="ds-file-name">
              <el-icon :size="14" style="color:var(--success); flex-shrink:0"><Document /></el-icon>
              <span class="file-name-text">{{ getLatestFile(src.key)!.file_name }}</span>
            </div>
            <div class="ds-file-meta">
              <span>{{ formatDate(getLatestFile(src.key)!.created_at) }}</span>
              <span>{{ formatFileSize(getLatestFile(src.key)!.file_size) }}</span>
            </div>
            <div v-if="getLatestFile(src.key)!.sheet_count" class="ds-file-sheets">
              识别到 {{ getLatestFile(src.key)!.sheet_count }} 个工作表
            </div>
          </div>

          <!-- 无数据提示 -->
          <div v-else class="ds-empty">
            <span class="ds-empty-text">尚未上传</span>
          </div>

          <!-- 操作按钮 -->
          <div class="ds-actions">
            <el-button
              :type="getLatestFile(src.key) ? 'default' : 'primary'"
              :loading="uploading === src.key"
              size="small"
              :disabled="!canUpload(src.key) && src.key !== 'MAIN'"
              @click="handleUpload(src.key)"
            >
              <el-icon style="margin-right:4px"><Upload /></el-icon>
              {{ getLatestFile(src.key) ? '重新导入' : '上传' }}
            </el-button>
          <el-button
              v-if="getLatestFile(src.key)"
              size="small"
              type="default"
              @click="goToMapping(src.key)"
            >
              查看映射
            </el-button>
            <!-- 调整项特殊按钮 -->
            <el-button
              v-if="src.key === 'ADJUSTMENT'"
              size="small"
              type="primary"
              @click="router.push(`/runs/${runId}/adjustments`)"
            >
              管理调整
            </el-button>
          </div>
        </div>
      </div>

      <!-- 导入须知 -->
      <div class="content-card" style="padding:16px 20px;">
        <div class="content-card-header" style="margin-bottom:8px">
          <div class="content-card-title" style="font-size:14px; font-weight:500; color:var(--text-secondary)">
            <el-icon :size="15" style="margin-right:4px"><InfoFilled /></el-icon>
            说明
          </div>
        </div>
        <ul class="import-notes">
          <li>仅 <strong>员工基础薪资</strong> 为必传项，其余数据按需导入</li>
          <li>系统自动识别 Sheet 类型和列映射，可在 <strong>查看映射</strong> 中确认和修改</li>
          <li>同一类型数据可多次导入，新数据与已有数据自动合并</li>
          <li>已核算的任务重新导入将生成新版本，并使当前核算结果失效</li>
          <li>原始 Excel 文件不会被修改，所有数据均可追溯来源</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-source-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.data-source-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 18px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.data-source-card:hover {
  border-color: #D1D5DB;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.data-source-card.card-disabled {
  opacity: 0.5;
}

/* 卡片头部 */
.ds-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.ds-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ds-title-group {
  flex: 1;
  min-width: 0;
}

.ds-title {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.ds-hint {
  display: block;
  font-size: 12px;
  color: var(--warning);
  margin-top: 1px;
}

/* 文件信息 */
.ds-file-info {
  flex: 1;
  min-height: 60px;
  padding: 8px 10px;
  background: #F9FAFB;
  border-radius: 6px;
  margin-bottom: 12px;
}

.ds-file-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.file-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ds-file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.ds-file-sheets {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 空状态 */
.ds-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60px;
}

.ds-empty-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* 操作按钮 */
.ds-actions {
  display: flex;
  gap: 8px;
}

/* 说明列表 */
.import-notes {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 13px;
  color: var(--text-tertiary);
  line-height: 1.8;
}

.import-notes li::before {
  content: '·';
  margin-right: 8px;
  color: var(--border);
}

@media (max-width: 1024px) {
  .data-source-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
