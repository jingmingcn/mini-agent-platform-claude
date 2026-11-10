import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminLayout from '@/layouts/AdminLayout.vue'

export const menuRoutes = [
  { path: '/dashboard', name: 'dashboard', meta: { title: '系统概览', icon: 'DataBoard' }, component: () => import('@/views/Dashboard.vue') },
  { path: '/agents', name: 'agents', meta: { title: '智能体管理', icon: 'Avatar' }, component: () => import('@/views/Agents.vue') },
  { path: '/models', name: 'models', meta: { title: '大模型配置', icon: 'Cpu' }, component: () => import('@/views/Models.vue') },
  { path: '/knowledge', name: 'knowledge', meta: { title: '知识库管理', icon: 'Collection' }, component: () => import('@/views/KnowledgeBases.vue') },
  { path: '/documents', name: 'documents', meta: { title: '文档管理', icon: 'Document' }, component: () => import('@/views/Documents.vue') },
  { path: '/prompts', name: 'prompts', meta: { title: 'Prompt 管理', icon: 'EditPen' }, component: () => import('@/views/Prompts.vue') },
  { path: '/conversations', name: 'conversations', meta: { title: '会话管理', icon: 'ChatDotRound' }, component: () => import('@/views/Conversations.vue') },
  { path: '/users', name: 'users', meta: { title: '用户管理', icon: 'User' }, component: () => import('@/views/Users.vue') },
  { path: '/tools', name: 'tools', meta: { title: '插件与工具', icon: 'Tools' }, component: () => import('@/views/Tools.vue') },
  { path: '/settings', name: 'settings', meta: { title: '系统设置', icon: 'Setting' }, component: () => import('@/views/Settings.vue') },
  { path: '/logs', name: 'logs', meta: { title: '调用日志与统计', icon: 'Histogram' }, component: () => import('@/views/Logs.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
    {
      path: '/',
      component: AdminLayout,
      redirect: '/dashboard',
      children: [
        ...menuRoutes,
        { path: '/agents/new', name: 'agent-new', meta: { title: '新建智能体', parent: '/agents' }, component: () => import('@/views/AgentEdit.vue') },
        { path: '/agents/:id', name: 'agent-edit', meta: { title: '编辑智能体', parent: '/agents' }, component: () => import('@/views/AgentEdit.vue') },
        { path: '/knowledge/:id', name: 'knowledge-detail', meta: { title: '知识库详情', parent: '/knowledge' }, component: () => import('@/views/KnowledgeDetail.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.path === '/login') return true
  if (!auth.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
  if (!auth.profile) {
    try { await auth.fetchMe() } catch { auth.logout(); return { path: '/login' } }
  }
  return true
})

export default router
