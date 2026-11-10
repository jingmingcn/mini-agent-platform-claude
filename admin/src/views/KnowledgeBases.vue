<template>
  <div class="page">
    <div class="page-header">
      <div><h2>知识库管理</h2><div class="sub">每个知识库独立配置 Embedding、切片与检索参数，可被多个智能体联合检索</div></div>
      <el-button v-if="auth.canWrite" type="primary" icon="Plus" @click="openDialog(null)">新建知识库</el-button>
    </div>
    <div class="toolbar"><el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 240px" prefix-icon="Search" @change="load" /></div>
    <el-row :gutter="16" v-loading="loading">
      <el-col v-for="kb in list" :key="kb.id" :xs="24" :sm="12" :lg="8" style="margin-bottom: 16px">
        <div class="card kb" @click="$router.push(`/knowledge/${kb.id}`)">
          <div class="kb-top">
            <div class="kb-icon">📚</div>
            <div style="flex: 1; min-width: 0">
              <div class="kb-name">{{ kb.name }}</div>
              <div class="muted ellipsis">{{ kb.description || '暂无描述' }}</div>
            </div>
            <el-tag size="small" :type="kb.status === 'active' ? 'success' : 'info'">{{ kb.status === 'active' ? '启用' : '停用' }}</el-tag>
          </div>
          <div class="kb-stats">
            <div><b>{{ kb.document_count }}</b><span>文档</span></div>
            <div><b>{{ kb.chunk_count }}</b><span>切片</span></div>
            <div><b>{{ kb.embedding_dim || '-' }}</b><span>维度</span></div>
          </div>
          <div class="muted">Embedding：{{ embedName(kb) }} · 切片 {{ kb.chunk_size }}/{{ kb.chunk_overlap }}</div>
          <div class="kb-actions" v-if="auth.canWrite" @click.stop>
            <el-button size="small" text icon="Edit" @click="openDialog(kb)">编辑</el-button>
            <el-popconfirm title="删除知识库将同时删除全部文档与向量，确认？" @confirm="remove(kb)">
              <template #reference><el-button size="small" text type="danger" icon="Delete">删除</el-button></template>
            </el-popconfirm>
          </div>
        </div>
      </el-col>
      <el-col v-if="!loading && !list.length" :span="24"><el-empty description="还没有知识库" /></el-col>
    </el-row>
    <KbFormDialog v-model="dialog" :kb="editing" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { kbApi, modelApi } from '@/api'
import type { KnowledgeBase, LLMConfig } from '@/api/types'
import KbFormDialog from '@/components/KbFormDialog.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref<KnowledgeBase[]>([])
const models = ref<LLMConfig[]>([])
const loading = ref(false)
const keyword = ref('')
const dialog = ref(false)
const editing = ref<KnowledgeBase | null>(null)

function embedName(kb: KnowledgeBase) {
  if (!kb.embedding_llm_config_id) return 'local-hash（内置）'
  const m = models.value.find((x) => x.id === kb.embedding_llm_config_id)
  return kb.embedding_model || m?.embedding_model || '未知'
}
async function load() { loading.value = true; try { list.value = await kbApi.list(keyword.value || undefined) } finally { loading.value = false } }
function openDialog(kb: KnowledgeBase | null) { editing.value = kb; dialog.value = true }
async function remove(kb: KnowledgeBase) { await kbApi.remove(kb.id); ElMessage.success('已删除'); load() }
onMounted(async () => { load(); models.value = await modelApi.list() })
</script>

<style scoped>
.kb { cursor: pointer; transition: box-shadow .2s; }
.kb:hover { box-shadow: 0 6px 20px rgba(0,0,0,.08); }
.kb-top { display: flex; gap: 12px; align-items: center; }
.kb-icon { font-size: 26px; }
.kb-name { font-weight: 600; font-size: 15px; }
.ellipsis { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.kb-stats { display: flex; gap: 24px; margin: 14px 0 10px; }
.kb-stats div { display: flex; flex-direction: column; }
.kb-stats b { font-size: 20px; }
.kb-stats span { color: #8a919f; font-size: 12px; }
.kb-actions { margin-top: 8px; border-top: 1px solid #f0f2f5; padding-top: 6px; }
</style>
