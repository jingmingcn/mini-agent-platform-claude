<template>
  <div class="page">
    <div class="page-header"><div><h2>用户管理</h2><div class="sub">微信小程序用户与后台管理员账号</div></div></div>
    <div class="card">
      <el-tabs v-model="tab">
        <el-tab-pane label="小程序用户" name="users">
          <div class="toolbar">
            <el-input v-model="keyword" placeholder="搜索昵称" clearable style="width: 220px" @change="load" prefix-icon="Search" />
            <el-select v-model="status" placeholder="状态" clearable style="width: 120px" @change="load">
              <el-option label="正常" value="active" /><el-option label="禁用" value="disabled" />
            </el-select>
          </div>
          <el-table :data="users" v-loading="loading">
            <el-table-column label="用户" min-width="200"><template #default="{ row }: { row: any }">
              <div style="display: flex; gap: 8px; align-items: center"><el-avatar :size="30" :src="row.avatar_url || undefined">{{ (row.nickname || '?')[0] }}</el-avatar>
                {{ row.nickname || '未命名' }} <span class="muted">#{{ row.id }}</span></div></template></el-table-column>
            <el-table-column prop="conversation_count" label="会话数" width="90" />
            <el-table-column label="累计 Token" width="110"><template #default="{ row }: { row: any }">{{ fmtNum(row.total_tokens) }}</template></el-table-column>
            <el-table-column label="注册时间" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
            <el-table-column label="最近登录" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.last_login_at) }}</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{ row }: { row: any }">
              <el-switch :model-value="row.status === 'active'" :disabled="!auth.canWrite" @change="(v: any) => setStatus(row, v ? 'active' : 'disabled')" /></template></el-table-column>
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="load" /></div>
        </el-tab-pane>
        <el-tab-pane v-if="auth.isSuper" label="管理员" name="admins">
          <div class="toolbar"><el-button type="primary" icon="Plus" @click="openAdmin(null)">新建管理员</el-button></div>
          <el-table :data="admins">
            <el-table-column prop="username" label="用户名" width="160" />
            <el-table-column prop="display_name" label="显示名" width="160" />
            <el-table-column label="角色" width="130"><template #default="{ row }: { row: any }">{{ roleLabel[row.role as keyof typeof roleLabel] }}</template></el-table-column>
            <el-table-column label="状态" width="90"><template #default="{ row }: { row: any }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
            <el-table-column label="最近登录" min-width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.last_login_at) }}</template></el-table-column>
            <el-table-column label="操作" width="100"><template #default="{ row }: { row: any }"><el-button link type="primary" @click="openAdmin(row)">编辑</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
    <el-dialog v-model="adminDialog" :title="editingAdmin ? '编辑管理员' : '新建管理员'" width="480px">
      <el-form :model="adminForm" label-width="90px">
        <el-form-item label="用户名"><el-input v-model="adminForm.username" :disabled="!!editingAdmin" /></el-form-item>
        <el-form-item label="显示名"><el-input v-model="adminForm.display_name" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="adminForm.password" type="password" show-password :placeholder="editingAdmin ? '留空不修改' : '至少 8 位'" /></el-form-item>
        <el-form-item label="角色"><el-select v-model="adminForm.role">
          <el-option v-for="(v, k) in roleLabel" :key="k" :label="v" :value="k" /></el-select></el-form-item>
        <el-form-item v-if="editingAdmin" label="启用"><el-switch v-model="adminForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="adminDialog = false">取消</el-button><el-button type="primary" @click="saveAdmin">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api'
import type { AdminProfile, EndUser } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { fmtNum, fmtTime } from '@/utils/format'

const auth = useAuthStore()
const roleLabel = { super_admin: '超级管理员', admin: '管理员', viewer: '只读' }
const tab = ref('users')
const users = ref<EndUser[]>([])
const keyword = ref('')
const status = ref('')
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const admins = ref<AdminProfile[]>([])
const adminDialog = ref(false)
const editingAdmin = ref<AdminProfile | null>(null)
const adminForm = reactive({ username: '', display_name: '', password: '', role: 'admin', is_active: true })

async function load() {
  loading.value = true
  try { const r = await userApi.list({ page: page.value, page_size: 20, keyword: keyword.value || undefined, status: status.value || undefined }); users.value = r.items; total.value = r.total } finally { loading.value = false }
}
async function setStatus(u: EndUser, s: string) { await userApi.setStatus(u.id, s); ElMessage.success('已更新'); load() }
async function loadAdmins() { admins.value = await userApi.admins() }
function openAdmin(a: AdminProfile | null) {
  editingAdmin.value = a
  Object.assign(adminForm, { username: a?.username || '', display_name: a?.display_name || '', password: '', role: a?.role || 'admin', is_active: a?.is_active ?? true })
  adminDialog.value = true
}
async function saveAdmin() {
  const payload: Record<string, unknown> = { ...adminForm }
  if (!adminForm.password) delete payload.password
  if (editingAdmin.value) { delete payload.username; await userApi.updateAdmin(editingAdmin.value.id, payload) }
  else await userApi.createAdmin(payload)
  adminDialog.value = false
  ElMessage.success('已保存')
  loadAdmins()
}
watch(tab, (t) => t === 'admins' && loadAdmins())
onMounted(load)
</script>
