<template>
  <div class="page">
    <div class="page-header"><div><h2>调用日志与统计</h2><div class="sub">模型调用（含 Token 消耗、耗时、错误）与管理员操作审计</div></div></div>
    <div class="card">
      <el-tabs v-model="tab">
        <el-tab-pane label="模型调用日志" name="api">
          <div class="toolbar">
            <el-select v-model="callType" placeholder="调用类型" clearable style="width: 140px" @change="reload">
              <el-option v-for="t in ['stream', 'chat', 'embedding', 'test']" :key="t" :label="t" :value="t" />
            </el-select>
            <el-select v-model="status" placeholder="状态" clearable style="width: 120px" @change="reload">
              <el-option label="success" value="success" /><el-option label="failed" value="failed" />
            </el-select>
            <el-button icon="Refresh" @click="load">刷新</el-button>
          </div>
          <el-table :data="logs" v-loading="loading" size="small">
            <el-table-column label="时间" width="165"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
            <el-table-column prop="call_type" label="类型" width="90" />
            <el-table-column prop="provider" label="Provider" width="100" />
            <el-table-column prop="model" label="模型" min-width="140" />
            <el-table-column label="Agent / User" width="110"><template #default="{ row }: { row: any }">{{ row.agent_id ?? '-' }} / {{ row.user_id ?? '-' }}</template></el-table-column>
            <el-table-column label="Tokens (入/出/总)" width="150"><template #default="{ row }: { row: any }">{{ row.prompt_tokens }} / {{ row.completion_tokens }} / {{ row.total_tokens }}</template></el-table-column>
            <el-table-column label="耗时" width="90"><template #default="{ row }: { row: any }">{{ row.latency_ms }}ms</template></el-table-column>
            <el-table-column label="状态" width="85"><template #default="{ row }: { row: any }"><el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="load" /></div>
        </el-tab-pane>
        <el-tab-pane v-if="auth.canWrite" label="操作审计" name="audit">
          <el-table :data="audits" v-loading="auditLoading" size="small">
            <el-table-column label="时间" width="165"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
            <el-table-column prop="admin_username" label="管理员" width="120" />
            <el-table-column prop="action" label="操作" width="130" />
            <el-table-column label="资源" width="180"><template #default="{ row }: { row: any }">{{ row.resource_type }} #{{ row.resource_id ?? '-' }}</template></el-table-column>
            <el-table-column label="详情" min-width="260"><template #default="{ row }: { row: any }"><span class="mono">{{ row.detail ? JSON.stringify(row.detail) : '' }}</span></template></el-table-column>
            <el-table-column prop="ip" label="IP" width="130" />
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="auditPage" :page-size="20" :total="auditTotal" layout="total, prev, pager, next" @current-change="loadAudit" /></div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { logApi } from '@/api'
import type { ApiLog, AuditLog } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const auth = useAuthStore()
const tab = ref('api')
const logs = ref<ApiLog[]>([])
const callType = ref('')
const status = ref('')
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const audits = ref<AuditLog[]>([])
const auditPage = ref(1)
const auditTotal = ref(0)
const auditLoading = ref(false)

async function load() {
  loading.value = true
  try { const r = await logApi.api({ page: page.value, page_size: 20, call_type: callType.value || undefined, status: status.value || undefined }); logs.value = r.items; total.value = r.total } finally { loading.value = false }
}
function reload() { page.value = 1; load() }
async function loadAudit() {
  auditLoading.value = true
  try { const r = await logApi.audit({ page: auditPage.value, page_size: 20 }); audits.value = r.items; auditTotal.value = r.total } finally { auditLoading.value = false }
}
watch(tab, (t) => t === 'audit' && loadAudit())
onMounted(load)
</script>
