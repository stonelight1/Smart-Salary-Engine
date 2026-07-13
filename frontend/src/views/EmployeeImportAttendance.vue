<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const uploading = ref(false)
const result = ref<any>(null)
const error = ref('')
const salaryMonth = ref('')

function handleUpload() {
  if (!salaryMonth.value) { ElMessage.warning('请选择工资月份'); return }
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    uploading.value = true
    error.value = ''
    result.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('salary_month', salaryMonth.value)
      
      const res = await fetch('/api/v1/attendance-compare/import', {
        method: 'POST', headers: {}, body: form,
      })
      const json = await res.json()
      if (json.success) result.value = json.data
      else error.value = json.message || '导入失败'
    } catch (err: any) { error.value = err.message || '导入失败' }
    finally { uploading.value = false }
  }
  input.click()
}

function goToChanges() { router.push('/employees/changes') }
function goToEmployees() { router.push('/employees') }
</script>

<template>
  <div class="page-layout">
    <div class="page-container">
      <div class="page-header">
        <div>
          <h1 class="page-title">导入考勤人员</h1>
          <p class="page-subtitle">上传本月考勤人员表，系统将自动比对员工档案并识别变化</p>
        </div>
        <el-button @click="goToEmployees">返回员工列表</el-button>
      </div>

      <div style="max-width:640px; margin:0 auto">
        <div class="content-card">
          <el-form label-position="top">
            <el-form-item label="目标月份" required>
              <el-date-picker v-model="salaryMonth" type="month" format="YYYY-MM" value-format="YYYY-MM"
                placeholder="选择月份" style="width:100%" size="large" />
            </el-form-item>
            <el-form-item>
              <div v-if="!result && !uploading" class="upload-zone" @click="handleUpload">
                <el-icon :size="36" style="color:var(--text-tertiary)"><UploadFilled /></el-icon>
                <p>点击上传考勤人员 Excel</p>
                <p class="upload-hint">支持 .xlsx、.xls 格式，将包含员工姓名、部门、岗位等信息</p>
              </div>
              <div v-if="uploading" class="upload-status"><el-icon :size="28" class="is-loading"><Loading /></el-icon><p>正在解析比对……</p></div>
              <div v-if="error" class="upload-error"><el-icon><WarningFilled /></el-icon><span>{{ error }}</span></div>
            </el-form-item>
          </el-form>

          <!-- Result card -->
          <div v-if="result" class="result-card">
            <h3>{{ salaryMonth }} 考勤人员识别完成</h3>
            <div class="result-grid">
              <div class="result-item"><span class="ri-label">有效员工</span><span class="ri-value">{{ (result.matched_count || 0) + (result.new_hire_count || 0) }}</span></div>
              <div class="result-item"><span class="ri-label">已匹配档案</span><span class="ri-value">{{ result.matched_count }}</span></div>
              <div class="result-item warn" v-if="result.new_hire_count"><span class="ri-label">疑似新入职</span><span class="ri-value">{{ result.new_hire_count }}</span></div>
              <div class="result-item warn" v-if="result.possible_terminations"><span class="ri-label">疑似离职</span><span class="ri-value">{{ result.possible_terminations }}</span></div>
              <div class="result-item warn" v-if="result.dept_changes"><span class="ri-label">部门变化</span><span class="ri-value">{{ result.dept_changes }}</span></div>
              <div class="result-item warn" v-if="result.pos_changes"><span class="ri-label">岗位变化</span><span class="ri-value">{{ result.pos_changes }}</span></div>
              <div class="result-item danger" v-if="result.conflicts"><span class="ri-label">信息冲突</span><span class="ri-value">{{ result.conflicts }}</span></div>
              <div class="result-item muted"><span class="ri-label">汇总行</span><span class="ri-value">{{ result.summary_count }}</span></div>
              <div class="result-item muted"><span class="ri-label">空白行</span><span class="ri-value">{{ result.empty_count }}</span></div>
            </div>
            <div class="result-actions">
              <el-button type="primary" @click="goToChanges" v-if="result.total_candidates > 0">处理员工变化</el-button>
              <el-button @click="goToEmployees">返回员工档案</el-button>
              <el-button @click="result = null">重新上传</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-zone { border: 2px dashed var(--border); border-radius: 10px; padding: 40px 20px; text-align: center; cursor: pointer; transition: border-color .15s; }
.upload-zone:hover { border-color: #2563EB; background: #F8FAFF; }
.upload-zone p { font-size: 14px; color: var(--text-primary); margin-top: 8px; }
.upload-hint { font-size: 12px !important; color: var(--text-tertiary) !important; margin-top: 4px !important; }
.upload-status { text-align: center; padding: 30px 0; }
.is-loading { animation: rotating 1.2s linear infinite; }
@keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.upload-error { display: flex; align-items: center; gap: 8px; padding: 12px; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; color: #DC2626; font-size: 13px; }
.result-card { border: 1px solid var(--border); border-radius: 10px; padding: 20px; }
.result-card h3 { font-size: 16px; font-weight: 600; margin-bottom: 14px; }
.result-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
.result-item { padding: 10px; background: #F9FAFB; border-radius: 6px; }
.ri-label { display: block; font-size: 12px; color: var(--text-tertiary); }
.ri-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.result-item.warn .ri-value { color: #D97706; }
.result-item.danger .ri-value { color: #DC2626; }
.result-item.muted .ri-value { color: var(--text-tertiary); }
.result-actions { display: flex; gap: 8px; }
</style>
