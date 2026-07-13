<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runApi } from '@/api'
import { formatMonth } from '@/utils'

const router = useRouter()

// ============ 基础表单 ============
const name = ref('')
const payrollMonth = ref('')
const remark = ref('')
const loading = ref(false)
const allRuns = ref<any[]>([])

// ============ 引用来源 ============
type RefType = 'SYSTEM_FINAL' | 'EXTERNAL_EXCEL' | 'NONE'
const refType = ref<RefType>('SYSTEM_FINAL')
const referenceRunId = ref('')
const referenceExternalId = ref('')

// 外部上传相关
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const parsedResult = ref<any>(null)
const parseError = ref('')
const referenceMonth = ref('')
const monthMismatchWarning = ref('')

// 引用月份智能检测
const detectedRefMonth = ref('')

// 获取上月最终版列表
onMounted(async () => {
  try {
    const res = await runApi.list({ page: 1, page_size: 50 })
    allRuns.value = (res.data.data.items || []).filter(
      (r: any) => r.status === 'LOCKED' || r.status === 'EXPORTED',
    )
  } catch {}
})

// 月份选择 → 自动生成名称 + 自动匹配引用
watch(payrollMonth, (val) => {
  if (!val) return
  if (!name.value) {
    name.value = `${formatMonth(val)}工资核算`
  }
  // 自动匹配上月系统版本
  const [year, month] = val.split('-')
  const pm = parseInt(month) - 1
  const py = pm === 0 ? parseInt(year) - 1 : parseInt(year)
  const ps = pm === 0 ? '12' : String(pm).padStart(2, '0')
  const prevKey = `${py}-${ps}`
  const match = allRuns.value.find((r: any) => r.payroll_month === prevKey)
  if (match) {
    referenceRunId.value = match.id
  }
  // 计算引用月份
  detectedRefMonth.value = prevKey
  referenceMonth.value = prevKey
})

const remarkCount = computed(() => remark.value.length)

// ============ 外部 Excel 上传 ============
function handleSelectFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    uploadFile.value = file
    parsedResult.value = null
    parseError.value = ''
    await parseFile(file)
  }
  input.click()
}

async function parseFile(file: File) {
  uploading.value = true
  parseError.value = ''
  try {
    const form = new FormData()
    form.append('file', file)
    
    const res = await fetch('/api/v2/reference/parse', {
      method: 'POST',
      headers: {},
      body: form,
    })
    const json = await res.json()
    if (json.success) {
      parsedResult.value = json.data
      // 尝试从文件名推测引用月份
      tryGuessRefMonth(file.name)
    } else {
      parseError.value = json.message || '解析失败'
    }
  } catch (err: any) {
    parseError.value = err.message || '解析失败'
  } finally {
    uploading.value = false
  }
}

function tryGuessRefMonth(fileName: string) {
  const monthMatch = fileName.match(/(\d{4})[年\-\.](\d{1,2})[月]/)
  if (monthMatch) {
    const guess = `${monthMatch[1]}-${monthMatch[2].padStart(2, '0')}`
    referenceMonth.value = guess
    if (payrollMonth.value && guess !== detectedRefMonth.value) {
      monthMismatchWarning.value =
        `当前创建的是 ${formatMonth(payrollMonth.value)} 工资任务，` +
        `上传文件疑似为 ${formatMonth(guess)} 工资表，请确认是否继续使用。`
    } else {
      monthMismatchWarning.value = ''
    }
  }
}

async function confirmReference() {
  if (!parsedResult.value || !uploadFile.value) return

  // 阻断异常检查
  const blocks = (parsedResult.value.issues || []).filter((i: any) => i.level === 'BLOCK')
  if (blocks.length > 0) {
    ElMessage.warning(`存在 ${blocks.length} 个阻断异常，请处理后再确认。`)
    return
  }

  // 月份不匹配时二次确认
  if (monthMismatchWarning.value) {
    try {
      await ElMessageBox.confirm(monthMismatchWarning.value + '\n\n是否继续使用该文件？', '月份不匹配', {
        confirmButtonText: '继续使用', cancelButtonText: '取消', type: 'warning',
      })
    } catch { return }
  }

  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', uploadFile.value)
    form.append('original_name', uploadFile.value.name)
    form.append('target_salary_month', payrollMonth.value || '')
    form.append('reference_salary_month', referenceMonth.value || detectedRefMonth.value || '')
    form.append('parsed_json', JSON.stringify(parsedResult.value))

    
    const res = await fetch('/api/v2/reference/save-from-upload', {
      method: 'POST',
      headers: {},
      body: form,
    })
    const json = await res.json()
    if (json.success) {
      referenceExternalId.value = json.data.reference_id
      ElMessage.success(`引用版本已保存，识别到 ${json.data.employee_count} 名员工`)
    } else {
      ElMessage.error(json.message || '保存失败')
    }
  } catch (err: any) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    uploading.value = false
  }
}

// ============ 创建任务 ============
async function handleCreate() {
  if (!payrollMonth.value) {
    ElMessage.warning('请选择工资月份')
    return
  }
  if (!name.value) {
    ElMessage.warning('请输入任务名称')
    return
  }

  // 外部 Excel 方式必须要保存引用版本
  if (refType.value === 'EXTERNAL_EXCEL' && !referenceExternalId.value) {
    if (!uploadFile.value) {
      ElMessage.warning('请先上传上月最终工资表')
      return
    }
    ElMessage.warning('请先「确认引用」后再创建任务')
    return
  }

  loading.value = true
  try {
    const params: any = {
      name: name.value,
      payroll_month: payrollMonth.value,
      remark: remark.value || undefined,
      run_version: 'DRAFT',
      reference_source_type: refType.value,
    }

    if (refType.value === 'SYSTEM_FINAL') {
      params.reference_run_id = referenceRunId.value || undefined
    } else if (refType.value === 'EXTERNAL_EXCEL') {
      params.reference_external_id = referenceExternalId.value
    }

    const res = await runApi.create(params)
    ElMessage.success('创建成功，即将进入任务详情')

    // 如果是外部引用，自动创建草稿
    if (refType.value === 'EXTERNAL_EXCEL' && referenceExternalId.value) {
      
      await fetch(`/api/v2/reference/${referenceExternalId.value}/confirm-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_run_id: res.data.data.id }),
      })
    }

    router.push(`/runs/${res.data.data.id}`)
  } catch (err: any) {
    const msg = err.response?.data?.message || '创建失败，请重试'
    ElMessage.error(msg)
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
        <span>新建任务</span>
      </div>

      <!-- 页面标题 -->
      <div class="page-header" style="padding-top:12px">
        <div class="page-header-left">
          <h1 class="page-title">新建工资核算任务</h1>
          <p class="page-subtitle">创建任务后，可继续导入绩效、请假数据并完成工资核算</p>
        </div>
      </div>

      <div style="max-width:760px; margin:0 auto">
        <!-- 基本信息 -->
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">
              <el-icon :size="18" style="color:var(--primary); background:#EFF6FF; padding:4px; border-radius:6px"><InfoFilled /></el-icon>
              任务基本信息
            </div>
          </div>
          <p style="font-size:13px; color:var(--text-tertiary); margin-bottom:20px; padding-left:30px;">
            一个工资月份建议只创建一个正式核算任务
          </p>
          <el-form label-position="top" style="max-width:520px">
            <el-form-item label="工资月份" required>
              <el-date-picker v-model="payrollMonth" type="month" format="YYYY-MM" value-format="YYYY-MM"
                placeholder="请选择核算月份" style="width:100%" size="large" />
            </el-form-item>
            <el-form-item label="任务名称" required>
              <el-input v-model="name" placeholder="选择月份后将自动生成" size="large" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="remark" type="textarea" :rows="2"
                placeholder="可填写本次核算范围、特殊说明等" maxlength="500" show-word-limit />
            </el-form-item>
          </el-form>
        </div>

        <!-- 引用数据来源 -->
        <div class="content-card" style="margin-top:16px">
          <div class="content-card-header">
            <div class="content-card-title">
              <el-icon :size="18" style="color:var(--primary); background:#EFF6FF; padding:4px; border-radius:6px"><Connection /></el-icon>
              引用数据来源
            </div>
          </div>

          <!-- 三段按钮选择 -->
          <div class="ref-type-tabs">
            <div class="ref-type-option" :class="{ active: refType === 'SYSTEM_FINAL' }" @click="refType = 'SYSTEM_FINAL'">
              <el-icon><Folder /></el-icon>
              <span>系统历史最终版</span>
              <span class="ref-desc">引用系统内已有最终版</span>
            </div>
            <div class="ref-type-option" :class="{ active: refType === 'EXTERNAL_EXCEL' }" @click="refType = 'EXTERNAL_EXCEL'">
              <el-icon><Upload /></el-icon>
              <span>上传Excel最终版</span>
              <span class="ref-desc">上传外部工资表</span>
            </div>
            <div class="ref-type-option" :class="{ active: refType === 'NONE' }" @click="refType = 'NONE'">
              <el-icon><Close /></el-icon>
              <span>不引用历史数据</span>
              <span class="ref-desc">手动导入所有数据</span>
            </div>
          </div>

          <!-- 方式一：系统历史最终版 -->
          <div v-if="refType === 'SYSTEM_FINAL'" class="ref-section">
            <el-form label-position="top" style="max-width:520px">
              <el-form-item label="引用上月最终版">
                <el-select v-model="referenceRunId" placeholder="选择上月工资最终版（可选）" clearable style="width:100%">
                  <el-option v-for="r in allRuns" :key="r.id" :label="`${r.name}（${r.payroll_month}）`" :value="r.id" />
                </el-select>
                <p style="font-size:12px; color:var(--text-tertiary); margin-top:4px">
                  选择引用版本后，系统将继承员工基础信息和工资标准
                </p>
              </el-form-item>
            </el-form>
          </div>

          <!-- 方式二：上传 Excel 最终版 -->
          <div v-if="refType === 'EXTERNAL_EXCEL'" class="ref-section">
            <!-- 上传区域 -->
            <div v-if="!parsedResult && !uploadFile" class="ref-upload-zone" @click="handleSelectFile">
              <el-icon :size="36" style="color:var(--text-tertiary)"><UploadFilled /></el-icon>
              <p>点击上传上月最终工资表</p>
              <p class="upload-hint">支持 .xlsx、.xls 格式</p>
            </div>

            <!-- 上传中 -->
            <div v-if="uploading && !parsedResult" class="ref-upload-status">
              <el-icon :size="28" class="is-loading" style="color:var(--primary)"><Loading /></el-icon>
              <p>正在解析上月工资表……</p>
            </div>

            <!-- 解析错误 -->
            <div v-if="parseError" class="ref-parse-error">
              <el-icon :size="20" style="color:var(--danger)"><WarningFilled /></el-icon>
              <span>{{ parseError }}</span>
              <el-button size="small" @click="handleSelectFile">重新选择文件</el-button>
            </div>

            <!-- 解析结果卡片 -->
            <div v-if="parsedResult && !parseError" class="ref-parse-card">
              <div class="rpc-header">
                <el-icon :size="18" style="color:var(--success)"><Document /></el-icon>
                <span class="rpc-filename">{{ uploadFile?.name }}</span>
              </div>
              <div class="rpc-info">
                <div class="rpc-row">
                  <span>识别工作表：<strong>{{ parsedResult.sheet_name }}</strong></span>
                </div>
                <div class="rpc-stats">
                  <span class="rpc-stat ok">员工：{{ parsedResult.employee_count }} 人</span>
                  <span class="rpc-stat muted">汇总行：{{ parsedResult.summary_row_count }} 行</span>
                  <span class="rpc-stat muted">空白行：{{ parsedResult.empty_row_count }} 行</span>
                  <span v-if="parsedResult.invalid_row_count" class="rpc-stat warn">异常：{{ parsedResult.invalid_row_count }} 条</span>
                </div>
                <div v-if="parsedResult.issues?.length" class="rpc-issues">
                  <div v-for="iss in parsedResult.issues" :key="iss.row" :class="'issue-' + (iss.level === 'BLOCK' ? 'block' : 'warn')">
                    <el-icon :size="14"><WarningFilled /></el-icon>
                    <span>{{ iss.message }}</span>
                  </div>
                </div>
              </div>

              <!-- 月份匹配提示 -->
              <div v-if="monthMismatchWarning" class="rpc-month-warn">
                <el-icon :size="16" style="color:var(--warning)"><Warning /></el-icon>
                <span>{{ monthMismatchWarning }}</span>
              </div>

              <div class="rpc-actions">
                <el-button size="small" @click="handleSelectFile">重新上传</el-button>
                <el-button size="small" type="primary" :loading="uploading"
                  :disabled="(parsedResult.issues || []).filter((i:any)=>i.level==='BLOCK').length > 0"
                  @click="confirmReference">
                  确认引用
                </el-button>
              </div>
            </div>
          </div>

          <!-- 方式三：不引用 -->
          <div v-if="refType === 'NONE'" class="ref-section">
            <div class="ref-none-hint">
              <el-icon :size="20" style="color:var(--text-tertiary)"><InfoFilled /></el-icon>
              <p>不引用历史工资数据，创建任务后需要手动导入或新增员工工资信息。</p>
            </div>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="content-card" style="margin-top:16px">
          <div style="display:flex; justify-content:flex-end; gap:12px">
            <el-button size="large" @click="router.push('/')"><el-icon><Close /></el-icon>取消</el-button>
            <el-button type="primary" size="large" :loading="loading" @click="handleCreate">
              <el-icon v-if="!loading"><Plus /></el-icon>{{ loading ? '创建中...' : '创建并进入下一步' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 三段选择按钮 */
.ref-type-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.ref-type-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: all .15s;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.ref-type-option:hover {
  border-color: #2563EB;
  background: #F8FAFF;
}
.ref-type-option.active {
  border-color: #2563EB;
  background: #EFF6FF;
}
.ref-desc {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-tertiary);
}
.ref-type-option.active .ref-desc {
  color: #2563EB;
}

/* 引用区域 */
.ref-section {
  padding: 0 2px;
}

/* 上传区域 */
.ref-upload-zone {
  border: 2px dashed var(--border);
  border-radius: 10px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color .15s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.ref-upload-zone:hover {
  border-color: #2563EB;
  background: #F8FAFF;
}
.ref-upload-zone p {
  font-size: 14px;
  color: var(--text-primary);
}
.upload-hint {
  font-size: 12px !important;
  color: var(--text-tertiary) !important;
}

/* 上传状态 */
.ref-upload-status {
  text-align: center;
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.is-loading {
  animation: rotating 1.2s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 解析错误 */
.ref-parse-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: 8px;
  font-size: 13px;
  color: #DC2626;
}

/* 解析结果卡片 */
.ref-parse-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}
.rpc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.rpc-filename {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.rpc-info {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}
.rpc-row {
  margin-bottom: 6px;
}
.rpc-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.rpc-stat.ok { color: #16A34A; }
.rpc-stat.muted { color: var(--text-tertiary); }
.rpc-stat.warn { color: #D97706; }
.rpc-issues {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rpc-issues > div {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}
.issue-block {
  background: #FEF2F2;
  color: #DC2626;
}
.issue-warn {
  background: #FFFBEB;
  color: #D97706;
}
.rpc-month-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 6px;
  font-size: 13px;
  color: #D97706;
  margin-bottom: 10px;
}
.rpc-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  border-top: 1px solid var(--border-light, #EEF0F3);
  padding-top: 12px;
}
.ref-none-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  background: #F9FAFB;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
