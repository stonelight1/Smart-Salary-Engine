import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/runs/create',
    name: 'RunCreate',
    component: () => import('@/views/RunCreateView.vue'),
  },
  {
    path: '/runs/:runId',
    name: 'RunDetail',
    component: () => import('@/views/RunDetailView.vue'),
  },
  {
    path: '/runs/:runId/import',
    name: 'RunImport',
    component: () => import('@/views/ImportView.vue'),
  },
  {
    path: '/runs/:runId/mapping',
    name: 'RunMapping',
    component: () => import('@/views/MappingView.vue'),
  },
  {
    path: '/runs/:runId/data-summary',
    name: 'RunDataSummary',
    component: () => import('@/views/DataSummaryView.vue'),
  },
  {
    path: '/runs/:runId/adjustments',
    name: 'RunAdjustments',
    component: () => import('@/views/AdjustmentView.vue'),
  },
  {
    path: '/runs/:runId/data-pool',
    name: 'RunDataPool',
    component: () => import('@/views/DataPoolView.vue'),
  },
  {
    path: '/runs/:runId/check',
    name: 'RunCheck',
    component: () => import('@/views/CheckView.vue'),
  },
  {
    path: '/runs/:runId/issues',
    name: 'RunIssues',
    component: () => import('@/views/IssuesView.vue'),
  },
  {
    path: '/runs/:runId/calculate',
    name: 'RunCalculate',
    component: () => import('@/views/CalculateView.vue'),
  },
  {
    path: '/runs/:runId/explain',
    name: 'RunExplain',
    component: () => import('@/views/ExplainView.vue'),
  },
  {
    path: '/runs/:runId/export',
    name: 'RunExport',
    component: () => import('@/views/ExportView.vue'),
  },
  {
    path: '/runs/:runId/v2',
    name: 'SalaryV2',
    component: () => import('@/views/SalaryV2View.vue'),
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/views/ConfigView.vue'),
  },
  // ---- 员工档案 ----
  {
    path: '/employees',
    name: 'EmployeeList',
    component: () => import('@/views/EmployeeListView.vue'),
  },
  {
    path: '/employees/changes',
    name: 'EmployeeChanges',
    component: () => import('@/views/EmployeeChangeCandidates.vue'),
  },
  {
    path: '/employees/import-attendance',
    name: 'EmployeeImportAttendance',
    component: () => import('@/views/EmployeeImportAttendance.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
