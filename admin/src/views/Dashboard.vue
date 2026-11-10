<template>
  <div class="page" v-loading="loading">
    <div class="page-header"><div><h2>系统概览</h2><div class="sub">平台运行状态与调用统计</div></div>
      <el-button icon="Refresh" @click="load">刷新</el-button></div>
    <template v-if="data">
      <el-row :gutter="16">
        <el-col :xs="12" :md="6" v-for="s in stats" :key="s.label" style="margin-bottom: 16px">
          <StatCard v-bind="s" />
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :md="16" style="margin-bottom: 16px">
          <div class="card"><div class="section-title">近 14 天调用趋势</div><TrendChart :data="data.trend" /></div>
        </el-col>
        <el-col :md="8" style="margin-bottom: 16px">
          <div class="card" style="height: 100%">
            <div class="section-title">热门智能体（14 天）</div>
            <el-empty v-if="!data.top_agents.length" description="暂无数据" :image-size="80" />
            <div v-for="(a, i) in data.top_agents" :key="a.id" class="rank">
              <span class="no" :class="{ top: i < 3 }">{{ i + 1 }}</span><span class="name">{{ a.name }}</span>
              <span class="muted">{{ a.requests }} 次</span>
            </div>
            <el-divider />
            <div class="muted">用户反馈：👍 {{ data.likes }} · 👎 {{ data.dislikes }}</div>
          </div>
        </el-col>
      </el-row>
      <div class="card">
        <div class="section-title">最近调用日志</div>
        <el-table :data="data.recent_logs" size="small">
          <el-table-column label="时间" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
          <el-table-column prop="call_type" label="类型" width="90" />
          <el-table-column prop="model" label="模型" min-width="140" />
          <el-table-column prop="total_tokens" label="Tokens" width="90" />
          <el-table-column label="耗时" width="90"><template #default="{ row }: { row: any }">{{ row.latency_ms }} ms</template></el-table-column>
          <el-table-column label="状态" width="90"><template #default="{ row }: { row: any }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag></template></el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { logApi } from '@/api'
import type { Overview } from '@/api/types'
import StatCard from '@/components/StatCard.vue'
import TrendChart from '@/components/TrendChart.vue'
import { fmtNum, fmtTime } from '@/utils/format'

const data = ref<Overview>()
const loading = ref(false)
const stats = computed(() => {
  const d = data.value!
  return [
    { label: '智能体', value: d.agents, hint: `已发布 ${d.published_agents}`, icon: 'Avatar', color: '#6366f1' },
    { label: '模型配置', value: d.models, icon: 'Cpu', color: '#0ea5e9' },
    { label: '知识库', value: d.knowledge_bases, icon: 'Collection', color: '#10b981' },
    { label: '文档', value: d.documents, icon: 'Document', color: '#f59e0b' },
    { label: '用户', value: d.users, hint: `会话 ${d.conversations}`, icon: 'User', color: '#ec4899' },
    { label: '今日调用', value: d.today_calls, icon: 'ChatLineRound', color: '#8b5cf6' },
    { label: '今日 Token', value: fmtNum(d.today_tokens), icon: 'Coin', color: '#14b8a6' },
    { label: '累计 Token', value: fmtNum(d.total_tokens), icon: 'TrendCharts', color: '#ef4444' },
  ]
})
async function load() { loading.value = true; try { data.value = await logApi.overview() } finally { loading.value = false } }
onMounted(load)
</script>

<style scoped>
.rank { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
.rank .name { flex: 1; }
.no { width: 22px; height: 22px; border-radius: 6px; background: #eef0f4; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; }
.no.top { background: #3b82f6; color: #fff; }
</style>
