<template>
  <div class="page" v-if="kb">
    <div class="page-header">
      <div><h2>📚 {{ kb.name }}</h2><div class="sub">{{ kb.description || '暂无描述' }} · {{ kb.document_count }} 文档 · {{ kb.chunk_count }} 切片 · 集合 {{ kb.collection_name }}</div></div>
      <div>
        <el-button @click="$router.push('/knowledge')">返回</el-button>
        <template v-if="auth.canWrite">
          <el-button icon="Edit" @click="dialog = true">编辑配置</el-button>
          <el-popconfirm title="将清空向量并重新处理所有文档，确认？" @confirm="rebuild">
            <template #reference><el-button type="warning" icon="RefreshRight">重建索引</el-button></template>
          </el-popconfirm>
        </template>
      </div>
    </div>
    <div class="card">
      <el-tabs v-model="tab">
        <el-tab-pane label="文档" name="docs"><DocumentPanel ref="panel" :kb-id="kb.id" @changed="refresh" /></el-tab-pane>
        <el-tab-pane label="检索测试" name="search">
          <div class="toolbar">
            <el-input v-model="query" placeholder="输入问题，测试知识库检索效果" style="flex: 1; min-width: 260px" @keyup.enter="search" />
            <el-input-number v-model="topK" :min="1" :max="20" /><span class="muted" style="align-self: center">Top-K</span>
            <el-input-number v-model="threshold" :min="0" :max="1" :step="0.05" :precision="2" /><span class="muted" style="align-self: center">阈值</span>
            <el-button type="primary" :loading="searching" @click="search">检索</el-button>
          </div>
          <el-empty v-if="searched && !hits.length" description="没有超过阈值的结果，可尝试降低阈值" />
          <div v-for="h in hits" :key="h.chunk_id" class="hit">
            <div class="hit-head"><el-tag size="small">[{{ h.index }}]</el-tag><b>{{ h.document_name }}</b>
              <span class="muted" v-if="h.page_number">第 {{ h.page_number }} 页</span>
              <el-progress :percentage="Math.round(h.score * 100)" :stroke-width="6" style="width: 160px; margin-left: auto" /></div>
            <div class="pre">{{ h.content }}</div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="配置" name="config">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Embedding 配置 ID">{{ kb.embedding_llm_config_id || '内置 local-hash' }}</el-descriptions-item>
            <el-descriptions-item label="Embedding 模型">{{ kb.embedding_model || '（使用模型配置默认）' }}</el-descriptions-item>
            <el-descriptions-item label="向量维度">{{ kb.embedding_dim || '-' }}</el-descriptions-item>
            <el-descriptions-item label="向量数据库">{{ kb.vector_store }} / {{ kb.collection_name }}</el-descriptions-item>
            <el-descriptions-item label="切片大小">{{ kb.chunk_size }}</el-descriptions-item>
            <el-descriptions-item label="切片重叠">{{ kb.chunk_overlap }}</el-descriptions-item>
            <el-descriptions-item label="Top-K">{{ kb.top_k }}</el-descriptions-item>
            <el-descriptions-item label="相似度阈值">{{ kb.score_threshold }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ fmtTime(kb.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ kb.status }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </div>
    <KbFormDialog v-model="dialog" :kb="kb" @saved="refresh" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { kbApi } from '@/api'
import type { Citation, KnowledgeBase } from '@/api/types'
import DocumentPanel from '@/components/DocumentPanel.vue'
import KbFormDialog from '@/components/KbFormDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const kb = ref<KnowledgeBase>()
const tab = ref('docs')
const dialog = ref(false)
const panel = ref<InstanceType<typeof DocumentPanel>>()
const query = ref('')
const topK = ref(5)
const threshold = ref(0.3)
const hits = ref<Citation[]>([])
const searching = ref(false)
const searched = ref(false)

async function refresh() {
  kb.value = await kbApi.get(Number(route.params.id))
}
async function rebuild() {
  const r = await kbApi.rebuild(kb.value!.id)
  ElMessage.success(`已提交重建，共 ${r.documents} 个文档`)
  panel.value?.load()
  refresh()
}
async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try { hits.value = await kbApi.search(kb.value!.id, query.value, topK.value, threshold.value); searched.value = true } finally { searching.value = false }
}
onMounted(async () => { await refresh(); topK.value = kb.value!.top_k; threshold.value = kb.value!.score_threshold })
</script>

<style scoped>
.hit { border: 1px solid #eef0f4; border-radius: 8px; padding: 12px; margin-bottom: 10px; font-size: 13px; line-height: 1.7; }
.hit-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
</style>
