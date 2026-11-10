<template>
  <div class="page">
    <div class="page-header">
      <div><h2>文档管理</h2><div class="sub">按知识库查看文档解析状态、切片结果与失败原因</div></div>
      <el-select v-model="kbId" placeholder="选择知识库" style="width: 260px" filterable>
        <el-option v-for="kb in kbs" :key="kb.id" :label="`${kb.name}（${kb.document_count}）`" :value="kb.id" />
      </el-select>
    </div>
    <div class="card">
      <DocumentPanel v-if="kbId" :kb-id="kbId" />
      <el-empty v-else description="请先创建知识库" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { kbApi } from '@/api'
import type { KnowledgeBase } from '@/api/types'
import DocumentPanel from '@/components/DocumentPanel.vue'

const kbs = ref<KnowledgeBase[]>([])
const kbId = ref<number>()
onMounted(async () => { kbs.value = await kbApi.list(); kbId.value = kbs.value[0]?.id })
</script>
