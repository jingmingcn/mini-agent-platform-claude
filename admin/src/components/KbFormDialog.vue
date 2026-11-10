<template>
  <el-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" :title="kb ? '编辑知识库' : '新建知识库'" width="600px">
    <el-form :model="form" label-width="120px">
      <el-form-item label="名称" required><el-input v-model="form.name" maxlength="128" /></el-form-item>
      <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
      <el-form-item label="Embedding 模型">
        <el-select v-model="form.embedding_llm_config_id" clearable placeholder="内置 local-hash（离线演示用）" style="width: 100%">
          <el-option v-for="m in embedModels" :key="m.id" :label="`${m.name}（${m.embedding_model}）`" :value="m.id" />
        </el-select>
        <div class="muted">DeepSeek / Kimi 暂无 Embedding 接口，推荐 Qwen text-embedding-v3、OpenAI、SiliconFlow bge-m3。</div>
      </el-form-item>
      <el-form-item label="向量数据库"><el-tag>Qdrant</el-tag></el-form-item>
      <el-row>
        <el-col :span="12"><el-form-item label="切片大小"><el-input-number v-model="form.chunk_size" :min="100" :max="4000" :step="50" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="切片重叠"><el-input-number v-model="form.chunk_overlap" :min="0" :max="1000" :step="10" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="默认 Top-K"><el-input-number v-model="form.top_k" :min="1" :max="20" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="相似度阈值"><el-input-number v-model="form.score_threshold" :min="0" :max="1" :step="0.05" :precision="2" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="状态"><el-radio-group v-model="form.status"><el-radio value="active">启用</el-radio><el-radio value="disabled">停用</el-radio></el-radio-group></el-form-item>
      <el-alert v-if="kb" type="warning" :closable="false" show-icon title="修改 Embedding 模型或切片参数后，需要「重建索引」才能对已有文档生效。" />
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { kbApi, modelApi } from '@/api'
import type { KnowledgeBase, LLMConfig } from '@/api/types'

const props = defineProps<{ modelValue: boolean; kb?: KnowledgeBase | null }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [KnowledgeBase] }>()
const models = ref<LLMConfig[]>([])
const embedModels = computed(() => models.value.filter((m) => m.embedding_model && m.enabled))
const saving = ref(false)
const blank = () => ({ name: '', description: '', category: '', embedding_llm_config_id: null as number | null,
  chunk_size: 500, chunk_overlap: 80, top_k: 5, score_threshold: 0.3, status: 'active' })
const form = reactive(blank())

watch(() => props.modelValue, (v) => {
  if (!v) return
  Object.assign(form, blank(), props.kb ? { ...props.kb, description: props.kb.description || '', category: props.kb.category || '' } : {})
})

async function submit() {
  if (!form.name) return ElMessage.warning('请输入名称')
  if (form.chunk_overlap >= form.chunk_size) return ElMessage.warning('切片重叠必须小于切片大小')
  saving.value = true
  try {
    const kb = props.kb ? await kbApi.update(props.kb.id, form) : await kbApi.create(form)
    emit('update:modelValue', false)
    emit('saved', kb)
    ElMessage.success('已保存')
    if (kb.needs_rebuild && kb.document_count > 0) {
      await ElMessageBox.confirm('Embedding 或切片参数已变更，是否立即重建索引？', '提示', { type: 'warning' })
      await kbApi.rebuild(kb.id)
      ElMessage.success('已开始重建')
    }
  } finally { saving.value = false }
}
onMounted(async () => { models.value = await modelApi.list() })
</script>
