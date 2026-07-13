<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || localStorage.getItem('user_info') ? JSON.parse(localStorage.getItem('user_info')!).username : '用户')

function handleLogout() {
  ElMessageBox.confirm('确认退出系统？', '提示', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'info',
  }).then(() => {
    authStore.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<template>
  <header class="app-header">
    <div class="app-header-inner">
      <div class="app-header-left">
        <div class="app-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="6" fill="#2563EB" />
            <path d="M8 14h12M14 8v12" stroke="#fff" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="14" cy="14" r="4" fill="#fff" fill-opacity="0.3" />
          </svg>
        </div>
        <div class="app-brand">
          <span class="app-name">智能工资核算</span>
          <span class="app-en-name">Smart Salary Engine</span>
        </div>
        <nav class="app-nav">
          <router-link to="/" class="nav-link" :class="{ active: $route.name === 'Home' }">工作台</router-link>
          <router-link to="/employees" class="nav-link" :class="{ active: $route.path.startsWith('/employees') }">员工档案</router-link>
          <router-link to="/config" class="nav-link" :class="{ active: $route.name === 'Config' }">设置</router-link>
        </nav>
      </div>
      <div class="app-header-right">
        <el-dropdown trigger="click" @command="(cmd: string) => cmd === 'logout' && handleLogout()">
          <span class="user-trigger">
            <el-avatar :size="32" style="background:#2563EB; color:#fff; font-size:14px; font-weight:500">
              {{ username.charAt(0).toUpperCase() }}
            </el-avatar>
            <span class="user-name">{{ username }}</span>
            <el-icon style="color:#9CA3AF; font-size:14px"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.app-header-inner {
  max-width: var(--max-width);
  height: 100%;
  margin: 0 auto;
  padding: 0 var(--page-padding);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-logo {
  display: flex;
  align-items: center;
}

.app-brand {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.app-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.app-en-name {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.2;
}

/* 导航 */
.app-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 24px;
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  padding: 6px 14px;
  border-radius: 6px;
  transition: all 0.12s;
  text-decoration: none;
}

.nav-link:hover {
  color: var(--text-primary);
  background: #F3F4F6;
}

.nav-link.active,
.nav-link.router-link-active {
  color: #2563EB;
  background: #EFF6FF;
}

.app-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}

.user-trigger:hover {
  background: #F3F4F6;
}

.user-name {
  font-size: 14px;
  color: var(--text-primary);
}
</style>
