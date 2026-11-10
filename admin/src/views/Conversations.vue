<template>
  <div class="page">
    <div class="page-header"><div><h2>会话管理</h2><div class="sub">查看所有用户与智能体的对话记录、引用来源与反馈</div></div></div>
    <div class="card">
      <div class="toolbar">
        <el-select v-model="agentId" placeholder="全部智能体" clearable style="width: 200px" @change="reload">
          <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索标题" clearable style="width: 220px" @change="reload" prefix-icon="Search" />
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="agent_name" label="智能体" width="150" />
        <el-table-column label="用户" width="140"><template #default="{ row }: { row: any }">{{ row.user_nickname || '-' }} <span class="muted">#{{ row.user_id }}</span></template></el-table-column>
        <el-table-column prop="message_count" label="消息数" width="80" />
        <el-table-column label="最近消息" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.last_message_at) }}</template></el-table-column>
        <el-table-column label="操作" width="140"><template #default="{ row }: { row: any }">
          <el-button link type="primary" @click="view(row)">查看</el-button>
          <el-popconfirm v-if="auth.canWrite" title="确认删除该会话？" @confirm="remove(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
        </template></el-table-column>
      </el-table>
      <div class="pager"><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="load" /></div>
    </div>
    <el-drawer v-model="drawer" :title="current?.title" size="55%">
      <div v-loading="msgLoading">
        <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
          <div class="meta">
            <el-tag size="small" :type="m.role === 'user' ? 'info' : 'success'">{{ m.role === 'user' ? '用户' : '助手' }}</el-tag>
            <span class="muted">{{ fmtTime(m.created_at) }}</span>
            <el-tag v-if="m.status !== 'completed'" size="small" type="warning">{{ m.status }}</el-tag>
            <span v-if="m.token_usage" class="muted">{{ m.token_usage.total_tokens }} tokens</span>
            <span v-if="m.latency_ms" class="muted">{{ m.latency_ms }}ms</span>
            <span v-if="m.feedback">{{ m.feedback > 0 ? '👍' : '👎' }}</span>
          </div>
          <div class="pre body">{{ m.content }}</div>
          <div v-if="m.attachments?.length" class="muted">附件：{{ m.attachments.map((a: any) => a.name).join('、') }}</div>
          <el-collapse v-if="m.citations?.length">
            <el-collapse-item :title="`引用来源（${m.citations.length}）`">
              <div v-for="c in m.citations" :key="c.chunk_id" class="cite">[{{ c.index }}] <b>{{ c.document_name }}</b>
                <span class="muted">score {{ c.score }}</span><div class="pre">{{ c.snippet }}</div></div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { agentApi, conversationApi } from '@/api'
import type { Agent, Conversation, Message } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const auth = useAuthStore()
const list = ref<Conversation[]>([])
const agents = ref<Agent[]>([])
const agentId = ref<number>()
const keyword = ref('')
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const drawer = ref(false)
const current = ref<Conversation>()
const messages = ref<Message[]>([])
const msgLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await conversationApi.list({ page: page.value, page_size: 20, agent_id: agentId.value, keyword: keyword.value || undefined })
    list.value = r.items; total.value = r.total
  } finally { loading.value = false }
}
function reload() { page.value = 1; load() }
async function view(c: Conversation) {
  current.value = c; drawer.value = true; msgLoading.value = true
  try { messages.value = (await conversationApi.messages(c.id)).items } finally { msgLoading.value = false }
}
async function remove(c: Conversation) { await conversationApi.remove(c.id); load() }
onMounted(async () => { load(); agents.value = await agentApi.list() })
</script>

<style scoped>
.msg { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; line-height: 1.7; }
.msg.user { background: #f4f6fa; }
.msg.assistant { background: #f0fdf4; }
.meta { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.cite { font-size: 12px; margin-bottom: 8px; }
</style>
