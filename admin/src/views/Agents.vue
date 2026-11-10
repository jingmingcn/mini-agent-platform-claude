<template>
  <div class="page">
    <div class="page-header">
      <div><h2>智能体管理</h2><div class="sub">创建、配置并发布面向不同业务场景的 AI 智能体</div></div>
      <el-button v-if="auth.canWrite" type="primary" icon="Plus" @click="$router.push('/agents/new')">新建智能体</el-button>
    </div>
    <div class="card">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索名称" clearable style="width: 220px" @change="load" prefix-icon="Search" />
        <el-select v-model="status" placeholder="状态" clearable style="width: 140px" @change="load">
          <el-option v-for="(v, k) in agentStatusMap" :key="k" :label="v.label" :value="k" />
        </el-select>
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column label="智能体" min-width="240">
          <template #default="{ row }: { row: any }">
            <div class="agent-cell">
              <span class="avatar">{{ row.avatar || '🤖' }}</span>
              <div><div class="name">{{ row.name }} <el-tag v-if="row.is_featured" size="small" type="warning">推荐</el-tag></div>
                <div class="muted">{{ row.description || '—' }}</div></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="模型" width="160"><template #default="{ row }: { row: any }">{{ row.llm_config_name || '默认模型' }}</template></el-table-column>
        <el-table-column label="能力" width="200">
          <template #default="{ row }: { row: any }">
            <el-tag v-if="row.enable_rag" size="small">RAG · {{ row.knowledge_base_ids.length }} 库</el-tag>
            <el-tag v-if="row.enable_memory" size="small" type="success" style="margin-left: 4px">记忆</el-tag>
            <el-tag v-if="row.enable_tools" size="small" type="warning" style="margin-left: 4px">工具</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="访问" width="80"><template #default="{ row }: { row: any }">{{ row.access_level === 'public' ? '公开' : '受限' }}</template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }: { row: any }">
          <el-tag :type="agentStatusMap[row.status].type" size="small">{{ agentStatusMap[row.status].label }}</el-tag></template></el-table-column>
        <el-table-column label="更新时间" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.updated_at) }}</template></el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }: { row: any }">
            <el-button link type="primary" @click="$router.push(`/agents/${row.id}`)">{{ auth.canWrite ? '编辑' : '查看' }}</el-button>
            <template v-if="auth.canWrite">
              <el-button v-if="row.status !== 'published'" link type="success" @click="publish(row.id, true)">发布</el-button>
              <el-button v-else link type="warning" @click="publish(row.id, false)">下线</el-button>
              <el-popconfirm title="确认删除该智能体？" @confirm="remove(row.id)">
                <template #reference><el-button link type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { agentApi } from '@/api'
import type { Agent } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { agentStatusMap, fmtTime } from '@/utils/format'

const auth = useAuthStore()
const list = ref<Agent[]>([])
const loading = ref(false)
const keyword = ref('')
const status = ref('')
async function load() {
  loading.value = true
  try { list.value = await agentApi.list({ keyword: keyword.value || undefined, status: status.value || undefined }) } finally { loading.value = false }
}
async function publish(id: number, on: boolean) {
  await (on ? agentApi.publish(id) : agentApi.offline(id))
  ElMessage.success(on ? '已发布，小程序用户现在可以看到该智能体' : '已下线')
  load()
}
async function remove(id: number) { await agentApi.remove(id); ElMessage.success('已删除'); load() }
onMounted(load)
</script>

<style scoped>
.agent-cell { display: flex; gap: 10px; align-items: center; }
.avatar { width: 38px; height: 38px; border-radius: 10px; background: #eef2ff; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.name { font-weight: 600; }
</style>
